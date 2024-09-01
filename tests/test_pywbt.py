from __future__ import annotations

import shutil
import tempfile

import rasterio

from pywbt import whitebox_tools


def test_whitebox_tools(wbt_zipfile: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copy("tests/dem.tif", temp_dir)
        wbt_args = {
            "BreachDepressions": [
                "-i=dem.tif",
                "--fill_pits",
                "-o=dem_corr.tif",
            ],
            "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
            "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=streams.tif"],
        }
        # To avoid redownloading and hitting the WBT server multiple times for testing
        # on different platforms and Python versions, especially on CI, the binareis are
        # stored in `tests/wbt_zip` directory.
        whitebox_tools(
            wbt_args,
            wbt_root=f"{temp_dir}/wbt",
            work_dir=temp_dir,
            zip_path=f"tests/wbt_zip/{wbt_zipfile}",
        )
        with rasterio.open(f"{temp_dir}/streams.tif") as src:
            assert src.width == 233
            assert src.height == 303
            data = src.read(1)
            assert abs(data.mean() - 3218.5708) < 1e-3
