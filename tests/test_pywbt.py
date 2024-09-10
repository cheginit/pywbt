from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import rasterio

import pywbt


def test_whitebox_tools(wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    }
    # To avoid redownloading and hitting the WBT server multiple times for testing
    # on different platforms and Python versions, especially on CI, the binaries are
    # stored in `tests/wbt_zip` directory.
    with tempfile.TemporaryDirectory(prefix="test_", dir=".") as tmpdir:
        shutil.copy("tests/dem.tif", tmpdir)
        pywbt.whitebox_tools(
            tmpdir,
            wbt_args,
            ["streams.tif"],
            wbt_root=f"{tmpdir}/WBT",
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
    with rasterio.open("streams.tif") as src:
        assert src.width == 233
        assert src.height == 303
        data = src.read(1)
        data[data == src.nodata] = 0
        assert abs(data.mean() - 0.1243) < 1e-3
    Path("streams.tif").unlink()
