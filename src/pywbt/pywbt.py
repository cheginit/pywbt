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
    System = Literal["Windows", "Darwin", "Linux"]


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
def _get_platform_suffix() -> tuple[System, Platform]:
    """Determine the platform suffix for downloading WhiteboxTools."""
    system = platform.system()
    if system not in ("Windows", "Darwin", "Linux"):
        raise ValueError(f"Unsupported operating system: {system}")

    if system == "Windows":
        suffix = "win_amd64"
    elif system == "Darwin":
        suffix = "darwin_m_series" if platform.machine() == "arm64" else "darwin_amd64"
    else:
        suffix = "linux_musl" if "musl" in platform.libc_ver()[0].lower() else "linux_amd64"
    return system, suffix


def _extract_wbt(zip_path: Path, wbt_root: Path, temp_path: Path, system: System) -> None:
    """Extract WhiteboxTools from zip file."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(path=temp_path)

        wbt_dir = next(temp_path.glob("**/WBT"), None)
        shutil.copytree(str(wbt_dir), wbt_root, dirs_exist_ok=True)

        if system != "Windows":
            exec_path = wbt_root / "whitebox_tools"
            exec_path.chmod(exec_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        logger.info(f"Extracted WhiteboxTools to {wbt_root}")
    except zipfile.BadZipFile as e:
        raise RuntimeError("Downloaded file is not a valid zip file.") from e
    except FileNotFoundError as e:
        raise RuntimeError(f"Error extracting WhiteboxTools: {e}") from e
    except shutil.Error as e:
        raise RuntimeError(f"Error copying WhiteboxTools files: {e}") from e


def _download_wbt(
    wbt_root: str | Path,
    zip_path: str | Path | None,
    refresh_download: bool,
) -> None:
    """Download the WhiteboxTools executable for the current platform."""
    system, platform_suffix = _get_platform_suffix()
    url = BASE_URL.format(system, platform_suffix)
    wbt_root = Path(wbt_root)

    exe_name = "whitebox_tools.exe" if system == "Windows" else "whitebox_tools"
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

        _extract_wbt(zip_path, wbt_root, temp_path, system)


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
        raise RuntimeError(e.stderr) from e


class _WBTSession:
    """Context manager for running WhiteboxTools operations.

    Parameters
    ----------
    src_dir : Path
        Source directory containing input files.
    save_dir : Path, optional
        Directory to save the output files.
    files_to_save : tuple of str
        Files to save after the session. If ``None``, keep all intermediate files.
    """

    def __init__(
        self, src_dir: Path, save_dir: Path, files_to_save: tuple[str, ...] | None
    ) -> None:
        self.src_dir = src_dir
        self.files_to_save = files_to_save
        self.save_dir = save_dir
        self.system, _ = _get_platform_suffix()

    @staticmethod
    def _extract_outputs(wbt_args: dict[str, list[str]]) -> list[str]:
        """Extract output filenames from WhiteboxTools arguments."""
        outputs = []
        for args in wbt_args.values():
            outputs.extend(
                arg.split("=")[1] for arg in args if arg.startswith(("-o=", "--output="))
            )
        return outputs

    def run(
        self,
        wbt_args: dict[str, list[str]],
        wbt_root: str | Path,
        compress_rasters: bool,
        max_procs: int,
    ) -> None:
        """
        Run WhiteboxTools operations.

        Parameters
        ----------
        wbt_args : dict of str to list of str
            Arguments for WhiteboxTools.
        wbt_root : str or Path
            Root directory of WhiteboxTools.
        compress_rasters : bool
            Whether to compress rasters.
        max_procs : int
            Maximum number of processes to use.
        """
        exe_name = "whitebox_tools.exe" if self.system == "Windows" else "whitebox_tools"
        exe_path = Path(wbt_root) / exe_name
        self.outputs = self._extract_outputs(wbt_args)
        for tool_name, args in wbt_args.items():
            _run_wbt(exe_path, tool_name, args, max_procs, compress_rasters, self.src_dir)

    def __enter__(self) -> _WBTSession:  # noqa: PYI034
        logger.info(
            f"Starting WhiteboxTools session with source directory: {self.src_dir.absolute()}"
        )
        return self

    def __exit__(self, *_) -> None:
        if self.files_to_save is not None:
            for f in self.outputs:
                source = self.src_dir / f
                if not source.exists():
                    logger.exception(f"Output file to save {source} not found")
                    raise FileNotFoundError(f"Output file to save {source} not found")
                destination = Path(self.save_dir, f)
                if f in self.files_to_save:
                    shutil.move(source, destination)
                    logger.info(f"Moved output file {source} to {destination}")
                else:
                    source.unlink()
                    logger.info(f"Deleted intermediate file {source}")
        else:
            for file in self.outputs:
                shutil.move(file, self.save_dir)
        logger.info(
            f"Completed WhiteboxTools session with source directory: {self.src_dir.absolute()}"
        )


def whitebox_tools(
    src_dir: str | Path,
    arg_dict: dict[str, list[str]],
    files_to_save: list[str] | tuple[str, ...] | None = None,
    save_dir: str | Path = ".",
    wbt_root: str | Path = "WBT",
    compress_rasters: bool = False,
    zip_path: str | Path | None = None,
    refresh_download: bool = False,
    max_procs: int = -1,
    verbose: bool = False,
) -> None:
    """Run a WhiteboxTools (not Whitebox Runner) tool with specified arguments.

    Parameters
    ----------
    src_dir : str or Path
        Path to the source directory containing input files. All files in this directory
        will be copied to a temporary directory for processing by the WhiteboxTools.
        Note that when using these files in ``arg_dict``, you should use the filenames
        without the directory path since the internal working directory of the
        WhitboxTools is set to the temporary directory where the files are copied.
    arg_dict : dict
        A dictionary containing the tool names as keys and list of each
        tool's arguments as values. For example:
        ```python
        {
            "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
            "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
            "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
        }
        ```
        Note that the input and output file names should not contain the directory path,
        only the filenames.
    files_to_save : list, optional
        List of output files to save to ``save_dir``. Note that these should be the filenames
        without the directory path, just as they are used in the ``arg_dict``, i.e. the
        values that are passed by ``-o`` or ``--output``. Defaults to ``None``, which means
        all intermediate files will be saved to ``save_dir``.
    save_dir : str or Path, optional
        Path to the directory where the output files given in ``files_to_save`` will be saved
        (default is current working directory).
    wbt_root : str or Path, optional
        Path to the directory the Whitebox executables will be extracted to (default is "WBT").
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables (default is None).
        If None, the zip file will be downloaded to a temporary directory that gets
        deleted after the function finishes. Otherwise, the zip file will be saved to
        the specified path.
    refresh_download : bool, optional
        Whether to refresh the download if WhiteboxTools is found (default is False).
    compress_rasters : bool, optional
        Whether to compress output rasters (default is False).
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
    save_dir = Path(save_dir) if save_dir else Path.cwd()
    save_dir.mkdir(parents=True, exist_ok=True)

    _download_wbt(wbt_root, zip_path, refresh_download)

    if not isinstance(arg_dict, dict) or not all(
        isinstance(k, str) and isinstance(v, (list, tuple)) for k, v in arg_dict.items()
    ):
        raise ValueError("arg_dict must be a dict of str keys and list or tuple values.")

    if not isinstance(files_to_save, (list, tuple)):
        raise TypeError("files_to_save must be a list or tuple of strings.")

    with _WBTSession(Path(src_dir), Path(save_dir), tuple(files_to_save)) as wbt:
        wbt.run(arg_dict, wbt_root, compress_rasters, max_procs)
