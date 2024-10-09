"""Utility functions for getting and processing Digital Elevation Models (DEMs)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    import geopandas as gpd
    import xarray as xr


__all__ = ["get_nasadem", "get_3dep", "tif_to_da", "tif_to_gdf"]


class DependencyError(ImportError):
    """Raised when a required dependency is not found."""

    def __init__(self) -> None:
        self.message = "\n".join(
            (
                "The `dem_utils` module has additional dependencies that are not installed.",
                "Please install them using:",
                "`pip install 'geopandas>=1' planetary-computer pystac-client rioxarray`",
                "or:",
                "`micromamba install -c conda-forge 'geopandas-base>=1' planetary_computer pystac_client rioxarray`",
            )
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


def get_nasadem(
    bbox: tuple[float, float, float, float], tif_path: str | Path, to_utm: bool = False
) -> None:
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
        import geopandas as gpd
        import planetary_computer
        import pystac_client
        import rioxarray as rxr
        import rioxarray.merge as rxr_merge
        import shapely
    except ImportError as e:
        raise DependencyError from e

    bbox_buff = bbox_utm = bbox
    utm = 4326
    if to_utm:
        gdf = gpd.GeoSeries(shapely.box(*bbox), crs=4326)  # pyright: ignore[reportCallIssue]
        utm = gdf.estimate_utm_crs()
        bbox_utm = gdf.to_crs(utm).total_bounds
        buff_size, dem_res = 20, 30
        bbox_buff = gdf.to_crs(utm).buffer(buff_size * dem_res).to_crs(4326).total_bounds
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    signed_asset = (
        planetary_computer.sign(item.assets["elevation"]).href
        for item in catalog.search(collections=["nasadem"], bbox=bbox_buff).items()
    )
    dem = rxr_merge.merge_arrays(
        [rxr.open_rasterio(href).squeeze(drop=True) for href in signed_asset]  # pyright: ignore[reportArgumentType]
    )
    if to_utm:
        dem = dem.rio.reproject(utm).fillna(dem.rio.nodata).rio.clip_box(*bbox_utm)
    dem.attrs.update({"units": "meters", "vertical_datum": "EGM96"})
    dem.name = "elevation"
    dem.astype("int16").rio.to_raster(tif_path)
    dem.close()


def get_3dep(
    bbox: tuple[float, float, float, float],
    tif_path: str | Path,
    resolution: int = 10,
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
        import geopandas as gpd
        import numpy as np
        import rioxarray as rxr
        import shapely
    except ImportError as e:
        raise DependencyError from e

    base_url = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation"
    url = {
        10: f"{base_url}/13/TIFF/USGS_Seamless_DEM_13.vrt",
        30: f"{base_url}/1/TIFF/USGS_Seamless_DEM_1.vrt",
        60: f"{base_url}/2/TIFF/USGS_Seamless_DEM_2.vrt",
    }
    if resolution not in url:
        raise ValueError("Resolution must be one of 10, 30, or 60 meters.")
    bbox_buff = bbox_proj = bbox
    crs_proj = 4326
    if to_5070:
        gdf = gpd.GeoSeries(shapely.box(*bbox), crs=4326)  # pyright: ignore[reportCallIssue]
        crs_proj = 5070
        bbox_proj = gdf.to_crs(crs_proj).total_bounds
        buff_size = 20
        bbox_buff = gdf.to_crs(crs_proj).buffer(buff_size * resolution).to_crs(4326).total_bounds

    dem = cast("xr.DataArray", rxr.open_rasterio(url[resolution]).squeeze(drop=True))
    dem = dem.rio.clip_box(*bbox_buff)
    dem = dem.where(dem > dem.rio.nodata, drop=False).rio.write_nodata(np.nan)
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
