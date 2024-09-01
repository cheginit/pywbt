"""Python wrapper for WhiteboxTools command-line utility."""

from __future__ import annotations

import logging
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

BASE_URL = "https://www.whiteboxgeo.com/WBT_{}/WhiteboxTools_{}.zip"

__all__ = ["whitebox_tools"]

if TYPE_CHECKING:
    Platform = Literal["win_amd64", "darwin_m_series", "darwin_amd64", "linux_amd64", "linux_musl"]


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("pywbt")
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


logger = _setup_logger()


@lru_cache(maxsize=1)
def _get_platform_suffix() -> Platform:
    """Determine the platform suffix for downloading WhiteboxTools."""
    system = platform.system()
    if system not in ("Windows", "Darwin", "Linux"):
        raise ValueError(f"Unsupported operating system: {system}")

    if system == "Windows":
        return "win_amd64"
    elif system == "Darwin":
        return "darwin_m_series" if platform.machine() == "arm64" else "darwin_amd64"
    return "linux_musl" if "musl" in platform.libc_ver()[0].lower() else "linux_amd64"


def _extract_wbt(zip_path: Path, wbt_root: Path, temp_path: Path) -> None:
    """Extract WhiteboxTools from zip file."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if "/WBT/" in file_info.filename:
                    extracted_path = Path(
                        *Path(file_info.filename).parts[
                            Path(file_info.filename).parts.index("WBT") + 1 :
                        ]
                    )
                    if extracted_path.parts:
                        source = zip_ref.extract(file_info, path=temp_path)
                        dest = wbt_root / extracted_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(source, dest)

        if platform.system() != "Windows":
            for exec_name in ("whitebox_tools", "whitebox_runner"):
                exec_path = wbt_root / exec_name
                if exec_path.exists():
                    exec_path.chmod(
                        exec_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )

        logger.info(f"Extracted WhiteboxTools to {wbt_root}")
    except zipfile.BadZipFile as e:
        raise RuntimeError("Downloaded file is not a valid zip file.") from e


def _download_wbt(
    wbt_root: str | Path = "WBT", zip_path: str | Path | None = None, refresh_download: bool = False
) -> None:
    """Download the WhiteboxTools executable for the current platform."""
    platform_suffix = _get_platform_suffix()
    url = BASE_URL.format(platform.system(), platform_suffix)
    wbt_root = Path(wbt_root)

    exe_name = "whitebox_tools.exe" if platform.system() == "Windows" else "whitebox_tools"
    if (wbt_root / exe_name).exists() and not refresh_download:
        logger.info(f"Using existing WhiteboxTools executable: {wbt_root / exe_name}")
        return
    shutil.rmtree(wbt_root, ignore_errors=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / "whitebox_tools.zip" if zip_path is None else Path(zip_path)
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path = zip_path.with_suffix(".zip")

        if not zip_path.exists() or refresh_download:
            logger.info(f"Downloading WhiteboxTools from {url}")
            try:
                urllib.request.urlretrieve(url, zip_path)
            except urllib.error.URLError as e:
                raise RuntimeError(f"Failed to download WhiteboxTools: {e!s}") from e

        _extract_wbt(zip_path, wbt_root, temp_path)


@lru_cache(maxsize=1)
def _get_wbt_version(exe_path: str | Path) -> str:
    """Get the version of WhiteboxTools."""
    try:
        result = subprocess.run(
            [str(exe_path), "--version"], capture_output=True, text=True, check=True
        )
        match = re.search(r"WhiteboxTools v(\d+\.\d+\.\d+)", result.stdout.strip())
        return match.group(1) if match else "unknown"
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running WhiteboxTools: {e!s}") from e


def _run_wbt(
    exe_path: str | Path,
    tool_name: str,
    args: list[str],
    max_procs: int,
    compress_rasters: bool,
    work_dir: str | Path,
) -> None:
    """Run a WhiteboxTools command."""
    if tool_name in ("BreachDepressionsLeastCost", "breach_depressions_least_cost"):
        logger.warning("Forcing BreachDepressionsLeastCost to use a single process.")
        links = (
            "https://github.com/jblindsay/whitebox-tools/issues/418\n",
            "https://github.com/jblindsay/whitebox-tools/issues/416\n",
            "https://github.com/jblindsay/whitebox-tools/issues/407\n",
        )
        msg = " ".join(
            (
                "In WBT v2.4.0, BreachDepressionsLeastCost is unstable",
                ", for now, it is recommended to use BreachDepressions.",
                "For more information, see:\n",
                *links,
            )
        )
        logger.warning(msg)
        max_procs = 1

    command = [
        str(exe_path),
        f"--run={tool_name}",
        f"--wd={work_dir}",
        f"--compress_rasters={'true' if compress_rasters else 'false'}",
        f"--max_procs={max_procs}",
        *args,
    ]

    version = _get_wbt_version(exe_path)
    logger.info(f"Running WhiteboxTools version: {version}")
    logger.info(f"Command: {' '.join(map(str, command))}")

    try:
        process = subprocess.run(command, check=True, text=True, capture_output=True)
        logger.info("WhiteboxTools output:")
        logger.info(process.stdout)
    except subprocess.CalledProcessError as e:
        logger.exception("WhiteboxTools error output:")
        logger.exception(e.stderr)
        logger.exception("Error running WhiteboxTools")
        if "Error unwrapping 'output'" in e.stderr:
            raise RuntimeError(f"Retry after removing the working directory: {work_dir}") from e
        raise RuntimeError(e.stderr) from e


def whitebox_tools(
    arg_dict: dict[str, list[str]],
    wbt_root: str | Path = "WBT",
    work_dir: str | Path = "",
    compress_rasters: bool = False,
    zip_path: str | Path | None = None,
    refresh_download: bool = False,
    max_procs: int = -1,
    verbose: bool = False,
) -> None:
    """Run a WhiteboxTools (not Whitebox Runner) tool with specified arguments.

    Parameters
    ----------
    arg_dict : dict
        A dictionary containing the tool names as keys and list of each
        tool's arguments as values. For example:
        ``` py
        {
            "BreachDepressionsLeastCost": ["--dem='dem.tif'", "--output='breached_dem.tif'"],
            "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
        }
        ```
    wbt_root : str or Path, optional
        Path to the root directory containing the Whitebox executables (default is "WBT").
    work_dir : str or Path, optional
        Working directory for the tool (default is current directory).
    verbose : bool, optional
        Whether to print verbose output (default is False).
    compress_rasters : bool, optional
        Whether to compress output rasters (default is False).
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables (default is None).
        If None, the zip file will be downloaded to a temporary directory that gets
        deleted after the function finishes. Otherwise, the zip file will be saved to
        the specified path.
    refresh_download : bool, optional
        Whether to refresh the download if WhiteboxTools is found (default is False).
    max_procs : int, optional
        The maximum number of processes to use (default is 1).
    verbose : bool, optional
        Whether to print verbose output (default is False).

    Raises
    ------
    subprocess.CalledProcessError
        If the tool execution fails.
    Exception
        For any other unexpected errors.
    """
    logger.setLevel(logging.INFO if verbose else logging.WARNING)

    wbt_root = Path(wbt_root)
    work_dir = Path(work_dir) if work_dir else Path.cwd()
    work_dir.mkdir(parents=True, exist_ok=True)

    exe_name = "whitebox_tools.exe" if platform.system() == "Windows" else "whitebox_tools"
    exe_path = wbt_root / exe_name

    _download_wbt(wbt_root, zip_path, refresh_download)

    if not isinstance(arg_dict, dict) or not all(
        isinstance(k, str) and isinstance(v, (list, tuple)) for k, v in arg_dict.items()
    ):
        raise ValueError("arg_dict must be a dict of str keys and list or tuple values.")

    for tool_name, args in arg_dict.items():
        _run_wbt(exe_path, tool_name, args, max_procs, compress_rasters, work_dir)
