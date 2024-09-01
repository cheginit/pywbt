"""Utility functions for the examples."""

from __future__ import annotations

from typing import TYPE_CHECKING

import geopandas as gpd
import numpy as np
import planetary_computer
import pystac_client
import rasterio
import rioxarray
import rioxarray.merge as rxr_merge
import shapely
from rasterio import features

if TYPE_CHECKING:
    from pathlib import Path


def get_nasadem(
    bbox: tuple[float, float, float, float], tiff_path: str | Path, to_utm: bool = False
) -> None:
    """Download a Digital Elevation Model (DEM) for a given bounding box from NASADEM.

    Parameters
    ----------
    bbox : tuple
        Bounding box coordinates in the order (west, south, east, north) in decimal degrees.
    tiff_path : str or pathlib.Path
        Path to save the GeoTIFF file
    to_utm : bool, optional
        Reproject the DEM to UTM, by default False.
    """
    bbox_buff = bbox_utm = bbox
    utm = 4326
    if to_utm:
        gdf = gpd.GeoSeries(shapely.box(*bbox), crs=4326)
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
        [rioxarray.open_rasterio(href).squeeze(drop=True) for href in signed_asset]
    )
    if to_utm:
        dem = dem.rio.reproject(utm).fillna(dem.rio.nodata)
        dem = dem.rio.clip_box(*bbox_utm).astype("int16")
    dem.rio.to_raster(tiff_path)


def tiff_to_gdf(
    tiff_path: str | Path, dtype: str, feat_name: str, connectivity: int = 8
) -> gpd.GeoDataFrame:
    """Convert a GeoTIFF to a GeoDataFrame.

    Parameters
    ----------
    tiff_path : str or pathlib.Path
        Path to the GeoTIFF file. The file must contain a single band.
    dtype : str
        String representation of the data type to use for the feature values, e.g. ``int32``.
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
    with rasterio.open(tiff_path) as src:
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
