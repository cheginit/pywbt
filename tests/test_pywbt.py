from __future__ import annotations

import shutil
import tempfile
from typing import Callable

import pytest
import rasterio

import pywbt
from pywbt.dem_utils import DependencyError

# To avoid redownloading and hitting the WBT server multiple times for testing
# on different platforms and Python versions, especially on CI, the binaries are
# stored in `tests/wbt_zip` directory.


def assert_results(output_tiff: str, expected: float) -> None:
    with rasterio.open(output_tiff) as src:
        assert src.width == 233
        assert src.height == 303
        data = src.read(1)
        data[data == src.nodata] = 0
        assert abs(data.mean() - expected) < 1e-4


@pytest.fixture
def wbt_args() -> dict[str, list[str]]:
    return {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    }


def test_leastcost(wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressionsLeastCost": ["-i=dem.tif", "--fill", "--dist=100", "-o=dem_corr.tif"],
        "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    }
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            save_dir=tmpdir,
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
        assert_results(f"{tmpdir}/streams.tif", 0.1149)


def test_same_src_dir(wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            ["streams.tif"],
            save_dir=tmpdir,
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
        assert_results(f"{tmpdir}/streams.tif", 0.1243)


def test_no_save(wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            save_dir=f"{tmpdir}/results",
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
        assert_results(f"{tmpdir}/results/streams.tif", 0.1243)


def test_with_save(wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            ["streams.tif"],
            save_dir=f"{tmpdir}/results",
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
        assert_results(f"{tmpdir}/results/streams.tif", 0.1243)


def test_wbt_error(wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    wbt_args["ExtractStreams"][0] = "--flow_accum="
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        with pytest.raises(RuntimeError):
            pywbt.whitebox_tools(
                tmpdir,
                wbt_args,
                save_dir=f"{tmpdir}/results",
                wbt_root=f"{tmpdir}/WBT",
                zip_path=f"tests/wbt_zip/{wbt_zipfile}",
            )


def test_wbt_wrong_output(wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        with pytest.raises(FileNotFoundError):
            pywbt.whitebox_tools(
                tmpdir,
                wbt_args,
                ["no_streams.tif"],
                save_dir=f"{tmpdir}/results",
                wbt_root=f"{tmpdir}/WBT",
                zip_path=f"tests/wbt_zip/{wbt_zipfile}",
            )


def test_wrong_platform(wrong_wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        shutil.copy(f"tests/wbt_zip/{wrong_wbt_zipfile}", f"{tmpdir}/{wrong_wbt_zipfile}")
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            ["streams.tif"],
            save_dir=tmpdir,
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"{tmpdir}/{wrong_wbt_zipfile}",
        )
        assert_results(f"{tmpdir}/streams.tif", 0.1243)


def test_tools() -> None:
    tools = pywbt.list_tools()
    assert "BreachDepressions" in tools
    for t in tools:
        assert isinstance(pywbt.tool_parameters(t), list)


def test_tif_to_gdf(wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
        "Basins": ["--d8_pntr=fdir.tif", "-o=basins.tif"],
    }
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            ["basins.tif"],
            save_dir=tmpdir,
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"{tmpdir}/{wbt_zipfile}",
        )
        basin_geo = pywbt.dem_utils.tif_to_gdf(f"{tmpdir}/basins.tif", "int32", "basin")
        assert basin_geo.area.idxmax() == 175


def test_optional_deps(block_optional_imports: Callable[..., None]) -> None:
    block_optional_imports("rioxarray", "geopandas", "shapely", "numpy", "rasterio")
    with pytest.raises(DependencyError):
        pywbt.dem_utils.get_3dep((-95.20, 29.70, -95.201, 29.701), "dem.tif")

    with pytest.raises(DependencyError):
        pywbt.dem_utils.get_nasadem((-95.20, 29.70, -95.201, 29.701), "dem.tif")

    with pytest.raises(DependencyError):
        pywbt.dem_utils.tif_to_da("dem.tif")

    with pytest.raises(DependencyError):
        pywbt.dem_utils.tif_to_gdf("dem.tif", "int32", "elevation")


def test_wrong_res() -> None:
    bbox = (-95.20, 29.70, -95.201, 29.701)
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        fname_3dep = f"{tmpdir}/3dep.tif"
        with pytest.raises(ValueError, match="Resolution must be one of 10, 30, or 60 meters."):
            pywbt.dem_utils.get_3dep(bbox, fname_3dep, resolution=29, to_5070=True)


def test_dem_utils() -> None:
    bbox = (-95.20, 29.70, -95.201, 29.701)
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        fname_3dep = f"{tmpdir}/3dep.tif"
        pywbt.dem_utils.get_3dep(bbox, fname_3dep, resolution=30, to_5070=True)
        d3 = pywbt.dem_utils.tif_to_da(fname_3dep)
        fname_nasadem = f"{tmpdir}/nasadem.tif"
        pywbt.dem_utils.get_nasadem(bbox, fname_nasadem, to_utm=True)
        dn = pywbt.dem_utils.tif_to_da(fname_nasadem, "int16", "elevation", "Elevation", -32768)
        assert d3.shape == (4, 4)
        assert dn.shape == (5, 5)
        assert d3.mean().item() == pytest.approx(dn.mean().item(), rel=1.3)
