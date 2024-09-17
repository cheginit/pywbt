from __future__ import annotations

import shutil
import tempfile

import pytest
import rasterio

import pywbt

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
