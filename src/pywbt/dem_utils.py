"""Utility functions for getting and processing Digital Elevation Models (DEMs)."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    import geopandas as gpd
    import xarray as xr

    Bbox = tuple[float, float, float, float]


__all__ = ["get_3dep", "get_nasadem", "tif_to_da", "tif_to_gdf"]


class DependencyError(ImportError):
    """Raised when a required dependency is not found."""

    def __init__(self) -> None:
        deps = "'geopandas>=1' planetary-computer pystac-client rioxarray seamless-3dep"
        self.message = "\n".join(
            (
                "The `dem_utils` module has additional dependencies that are not installed.",
                "Please install them using:",
                f"`pip install {deps}`",
                "or:",
                f"`micromamba install -c conda-forge {deps}`",
            )
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


def _check_bbox(bbox: Bbox) -> None:
    """Validate that bbox is in correct form."""
    if not isinstance(bbox, Iterable) or len(bbox) != 4 or not all(map(math.isfinite, bbox)):
        raise TypeError(
            "`bbox` must be a tuple of form (west, south, east, north) in decimal degrees."
        )


def _bbox_buffer(bbox: Bbox, buffer: float, crs_proj: int) -> tuple[Bbox, Bbox]:
    """Buffer a bounding box in WGS 84 and reproject to a given projected CRS."""
    try:
        import shapely
        from pyproj import Transformer
    except ImportError as e:
        raise DependencyError from e
    transformer = Transformer.from_crs(4326, crs_proj, always_xy=True)
    minx, miny = transformer.transform(bbox[0], bbox[1])
    maxx, maxy = transformer.transform(bbox[2], bbox[3])
    bbox_proj = (minx, miny, maxx, maxy)

    bbox_buff = shapely.box(*bbox_proj).buffer(buffer).bounds
    transformer = Transformer.from_crs(crs_proj, 4326, always_xy=True)
    minx, miny = transformer.transform(bbox_buff[0], bbox_buff[1])
    maxx, maxy = transformer.transform(bbox_buff[2], bbox_buff[3])
    bbox_buff = (minx, miny, maxx, maxy)
    return bbox_proj, bbox_buff


def _estimate_utm(bbox: Bbox) -> int:
    """Estimate UTM CRS based on centroid of a bbox in WGS 84."""
    try:
        from pyproj.aoi import AreaOfInterest
        from pyproj.database import query_utm_crs_info
    except ImportError as e:
        raise DependencyError from e

    minx, miny, maxx, maxy = bbox
    x_center = 0.5 * (minx + maxx)
    y_center = 0.5 * (miny + maxy)
    utm_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=x_center,
            south_lat_degree=y_center,
            east_lon_degree=x_center,
            north_lat_degree=y_center,
        ),
    )
    return int(utm_list[0].code)


def get_nasadem(bbox: Bbox, tif_path: str | Path, to_utm: bool = False) -> None:
    """Get DEM for a given bounding box from NASADEM.

    Parameters
    ----------
    bbox : tuple
        Bounding box coordinates in the order (west, south, east, north) in decimal degrees.
    tif_path : str or pathlib.Path
        Path to save the obtained data as a GeoTIFF file.
    to_utm : bool, optional
        Reproject the DEM to UTM, by default False.
    """
    try:
        import planetary_computer
        import pystac_client
        import rioxarray as rxr
        import rioxarray.merge as rxr_merge
        from seamless_3dep._https_download import stream_write
    except ImportError as e:
        raise DependencyError from e

    _check_bbox(bbox)
    bbox_buff = bbox_utm = bbox
    utm = 4326
    dem_res = 30
    if to_utm:
        utm = _estimate_utm(bbox)
        buff_size = 20
        bbox_utm, bbox_buff = _bbox_buffer(bbox, buff_size * dem_res, utm)
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    urls = [
        str(planetary_computer.sign(item.assets["elevation"]).href)
        for item in catalog.search(collections=["nasadem"], bbox=bbox_buff).items()
    ]
    Path("cache").mkdir(exist_ok=True)
    tiff_list = [
        Path("cache") / f"nasadem_{hashlib.sha256(href.encode()).hexdigest()}.tiff" for href in urls
    ]
    stream_write(urls, tiff_list)
    dem = rxr_merge.merge_arrays(
        [rxr.open_rasterio(f).squeeze(drop=True) for f in tiff_list]  # pyright: ignore[reportArgumentType]
    )
    if to_utm:
        dem = dem.rio.reproject(utm).fillna(dem.rio.nodata)
    dem = dem.rio.clip_box(*bbox_utm)
    dem.attrs.update({"units": "meters", "vertical_datum": "EGM96"})
    dem.name = "elevation"
    dem.astype("int16").rio.to_raster(tif_path)
    dem.close()


def get_3dep(
    bbox: Bbox,
    tif_path: str | Path,
    resolution: Literal[10, 30, 60] = 10,
    to_5070: bool = False,
) -> None:
    """Get DEM from USGS's 3D Hydrography Elevation Data Program (3DEP).

    Parameters
    ----------
    bbox : tuple
        Bounding box coordinates in the order (west, south, east, north)
        in decimal degrees.
    tif_path : str or pathlib.Path
        Path to save the obtained data as a GeoTIFF file.
    resolution : int, optional
        Resolution of the DEM in meters, by default 10.
    to_5070 : bool, optional
        Reproject the DEM to EPGS:5070, by default False.
    """
    try:
        import rioxarray as rxr
        import rioxarray.merge as rxr_merge
        import seamless_3dep as s3dep
    except ImportError as e:
        raise DependencyError from e

    bbox_buff = bbox_proj = bbox
    crs_proj = 4326
    if to_5070:
        crs_proj = 5070
        buff_size = 20
        bbox_proj, bbox_buff = _bbox_buffer(bbox, buff_size * resolution, crs_proj)

    tiff_list = s3dep.get_dem(bbox_buff, "cache", resolution)
    if len(tiff_list) > 1:
        dem = rxr_merge.merge_arrays(
            [rxr.open_rasterio(f).squeeze(drop=True) for f in tiff_list]  # pyright: ignore[reportArgumentType]
        )
    else:
        dem = rxr.open_rasterio(tiff_list[0]).squeeze(drop=True).rio.clip_box(*bbox_buff)
    if to_5070:
        dem = dem.rio.reproject(crs_proj).rio.clip_box(*bbox_proj)
    dem.attrs.update({"units": "meters", "vertical_datum": "NAVD88"})
    dem.name = "elevation"
    dem.rio.to_raster(tif_path)
    dem.close()


def tif_to_da(
    tif_path: str | Path,
    dtype: str | None = None,
    name: str | None = None,
    long_name: str | None = None,
    nodata: float | None = None,
) -> xr.DataArray:
    """Read a GeoTIFF file with a single band into an xarray DataArray.

    Parameters
    ----------
    tif_path : str or pathlib.Path
        Path to the GeoTIFF file with a single band.
    dtype : str, optional
        Data type to cast the data to, e.g. ``int32``, by default ``None``,
        i.e. use the data type from the GeoTIFF.
    name : str, optional
        Name to assign to the ``xarray.DataArray``, by default ``None``.
    long_name : str, optional
        Long name to assign to the ``xarray.DataArray``, by default ``None``.
    nodata : int or float, optional
        Value to use as ``da.rio.nodata``, by default ``None``, i.e.
        use the ``da.rio.nodata`` value from the GeoTIFF.

    Returns
    -------
    xarray.DataArray
        DataArray containing the GeoTIFF data.
    """
    try:
        import numpy as np
        import rioxarray as rxr
    except ImportError as e:
        raise DependencyError from e

    ds = rxr.open_rasterio(tif_path).squeeze(drop=True).load()
    ds.close()
    ds = cast("xr.DataArray", ds)
    if nodata is not None:
        ds = ds.rio.write_nodata(nodata)
    if dtype is None:
        dtype = str(ds.dtype)
    else:
        ds = ds.astype(dtype)
    if ds.rio.nodata is not None and np.issubdtype(dtype, np.floating):
        ds = ds.where(ds != ds.rio.nodata).rio.write_nodata(np.nan)
    if name:
        ds.attrs["name"] = name
    if long_name:
        ds.attrs["long_name"] = long_name
    return ds


def tif_to_gdf(
    tif_path: str | Path, dtype: str, feat_name: str, connectivity: int = 8
) -> gpd.GeoDataFrame:
    """Convert a GeoTIFF to a GeoDataFrame.

    Parameters
    ----------
    tif_path : str or pathlib.Path
        Path to the GeoTIFF file. The file must contain a single band.
    dtype : str
        String representation of the data type to use for the feature
        values, e.g. ``int32``.
    feat_name : str
        Name to assign to the feature values column.
    connectivity : int, optional
        Use 4 or 8 pixel connectivity for grouping pixels into features,
        by default 8.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame containing the features.
    """
    try:
        import geopandas as gpd
        import numpy as np
        import rasterio
        from rasterio import features
    except ImportError as e:
        raise DependencyError from e

    with rasterio.open(tif_path) as src:
        data = src.read(1).astype(dtype)
        nodata = np.nan if src.nodata is None else src.nodata
        feats_gen = features.shapes(
            data,
            mask=~np.isnan(data) if np.isnan(nodata) else data != nodata,
            transform=src.transform,
            connectivity=connectivity,
        )
        gdf = gpd.GeoDataFrame.from_features(
            [{"geometry": geom, "properties": {feat_name: val}} for geom, val in feats_gen],
            crs=src.crs,
        )
        gdf[feat_name] = gdf[feat_name].astype(dtype)  # pyright: ignore[reportCallIssue,reportArgumentType]
    return gdf
