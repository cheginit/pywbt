from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest
import rasterio

import pywbt

is_linux = platform.system() == "Linux"

# To avoid redownloading and hitting the WBT server multiple times for testing
# on different platforms and Python versions, especially on CI, the binaries are
# stored in `tests/wbt_zip` directory.


def assert_results(output_tiff: Path, expected: float) -> None:
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


def test_leastcost(temp_dir: str, wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressionsLeastCost": ["-i=dem.tif", "--fill", "--dist=100", "-o=dem_corr.tif"],
        "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    }
    shutil.copy("tests/dem.tif", temp_dir)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path("tests/wbt_zip") / wbt_zipfile,
    )
    assert_results(Path(temp_dir) / "streams.tif", 0.1149)


def test_same_src_dir(temp_dir: str, wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    shutil.copy("tests/dem.tif", temp_dir)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        ["streams.tif"],
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path("tests/wbt_zip") / wbt_zipfile,
    )
    assert_results(Path(temp_dir) / "streams.tif", 0.1243)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path("tests/wbt_zip") / wbt_zipfile,
    )
    assert_results(Path(temp_dir) / "streams.tif", 0.1243)


def test_no_save(temp_dir: str, wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    shutil.copy("tests/dem.tif", temp_dir)
    results_dir = Path(temp_dir) / "results"
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        save_dir=results_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path("tests/wbt_zip") / wbt_zipfile,
    )
    assert_results(results_dir / "streams.tif", 0.1243)


def test_with_save(temp_dir: str, wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    shutil.copy("tests/dem.tif", temp_dir)
    results_dir = Path(temp_dir) / "results"
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        ["streams.tif"],
        save_dir=results_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path("tests/wbt_zip") / wbt_zipfile,
    )
    assert_results(results_dir / "streams.tif", 0.1243)


def test_wbt_error(temp_dir: str, wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    wbt_args["ExtractStreams"][0] = "--flow_accum="
    shutil.copy("tests/dem.tif", temp_dir)
    with pytest.raises(RuntimeError):
        pywbt.whitebox_tools(
            temp_dir,
            wbt_args,
            save_dir=Path(temp_dir) / "results",
            wbt_root=Path(temp_dir) / "WBT",
            zip_path=Path("tests/wbt_zip") / wbt_zipfile,
        )


def test_wbt_wrong_output(temp_dir: str, wbt_zipfile: str, wbt_args: dict[str, list[str]]) -> None:
    shutil.copy("tests/dem.tif", temp_dir)
    with pytest.raises(FileNotFoundError):
        pywbt.whitebox_tools(
            temp_dir,
            wbt_args,
            ["no_streams.tif"],
            save_dir=Path(temp_dir) / "results",
            wbt_root=Path(temp_dir) / "WBT",
            zip_path=Path("tests/wbt_zip") / wbt_zipfile,
        )


def test_wrong_platform(
    temp_dir: str, wrong_wbt_zipfile: str, wbt_args: dict[str, list[str]]
) -> None:
    shutil.copy("tests/dem.tif", temp_dir)
    shutil.copy(Path("tests/wbt_zip") / wrong_wbt_zipfile, Path(temp_dir) / wrong_wbt_zipfile)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        ["streams.tif"],
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path(temp_dir) / wrong_wbt_zipfile,
    )
    assert_results(Path(temp_dir) / "streams.tif", 0.1243)


def test_tools() -> None:
    tools = pywbt.list_tools()
    assert "BreachDepressions" in tools
    for t in tools:
        assert isinstance(pywbt.tool_parameters(t), list)


def test_tif_to_gdf(temp_dir: str, wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
        "Basins": ["--d8_pntr=fdir.tif", "-o=basins.tif"],
    }
    shutil.copy("tests/dem.tif", temp_dir)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        ["basins.tif"],
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path(temp_dir) / wbt_zipfile,
    )
    basin_geo = pywbt.dem_utils.tif_to_gdf(Path(temp_dir) / "basins.tif", "int32", "basin")
    assert basin_geo.area.idxmax() == 175


def test_shp_out(temp_dir: str, wbt_zipfile: str) -> None:
    wbt_args = {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
        "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
        "RasterToVectorLines": ["-i=streams.tif", "-o=streams.shp"],
    }
    shutil.copy("tests/dem.tif", temp_dir)
    pywbt.whitebox_tools(
        temp_dir,
        wbt_args,
        ["streams.shp"],
        save_dir=temp_dir,
        wbt_root=Path(temp_dir) / "WBT",
        zip_path=Path(temp_dir) / wbt_zipfile,
    )
    assert Path(temp_dir, "streams.shp").stat().st_size == 179412


@pytest.mark.xfail(is_linux, reason="pyproj seem to have issues on Linux.")
def test_dem_3dep(temp_dir: str) -> None:
    bbox = (-95.201, 29.70, -95.20, 29.701)
    fname_3dep = Path(temp_dir) / "3dep.tif"
    pywbt.dem_utils.get_3dep(bbox, fname_3dep, resolution=30, to_5070=True)
    d3 = pywbt.dem_utils.tif_to_da(fname_3dep)
    assert d3.shape == (4, 4)
    assert d3.mean().item() == pytest.approx(8.49899)


@pytest.mark.xfail(is_linux, reason="pyproj seem to have issues on Linux.")
def test_dem_nasadem(temp_dir: str) -> None:
    bbox = (-95.201, 29.70, -95.20, 29.701)
    fname_nasadem = Path(temp_dir) / "nasadem.tif"
    pywbt.dem_utils.get_nasadem(bbox, fname_nasadem, to_utm=True)
    dn = pywbt.dem_utils.tif_to_da(fname_nasadem, "int16", "elevation", "Elevation", -32768)
    assert dn.shape == (5, 5)
    assert dn.mean().item() == pytest.approx(9.76)


@pytest.fixture
def valid_toml_file() -> Path:
    return Path("tests/config.toml")


@pytest.fixture
def invalid_toml_file_not_dict(tmp_path: Path) -> Path:
    content = """
    src_dir = "data/input"
    arg_dict = "not_a_dict"
    """
    toml_file = tmp_path / "invalid_config.toml"
    toml_file.write_text(content)
    return toml_file


@pytest.fixture
def invalid_toml_file_missing(tmp_path: Path) -> Path:
    content = """
    src_dir = "data/input"
    """
    toml_file = tmp_path / "invalid_config.toml"
    toml_file.write_text(content)
    return toml_file


def test_cli_valid_toml(valid_toml_file: Path):
    Path("tests/temp_dir_cli").mkdir(exist_ok=True, parents=True)
    shutil.copy("tests/dem.tif", "tests/temp_dir_cli/dem.tif")
    result = subprocess.run(
        ["pywbt", str(valid_toml_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert Path("tests", "temp_dir_cli", "dem_corr.tif").stat().st_size == 567662
    shutil.rmtree("tests/temp_dir_cli")


def test_cli_invalid_toml_missing(invalid_toml_file_missing: Path):
    result = subprocess.run(
        ["pywbt", str(invalid_toml_file_missing)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "The TOML file must define" in result.stderr


def test_cli_invalid_toml(invalid_toml_file_not_dict: Path):
    result = subprocess.run(
        ["pywbt", str(invalid_toml_file_not_dict)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "The TOML file must define" in result.stderr


def test_cli_missing_toml():
    result = subprocess.run(
        ["pywbt", "missing_config.toml"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "File not found" in result.stderr
