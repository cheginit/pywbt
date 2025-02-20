"""Python wrapper for WhiteboxTools command-line utility."""

from __future__ import annotations

import json
import logging
import platform
import re
import shutil
import stat
import subprocess
import urllib.error
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Literal

from filelock import SoftFileLock

BASE_URL = "https://www.whiteboxgeo.com/WBT_{}/WhiteboxTools_{}.zip"

__all__ = ["list_tools", "prepare_wbt", "tool_parameters", "whitebox_tools"]

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    Platform = Literal["win_amd64", "darwin_m_series", "darwin_amd64", "linux_amd64", "linux_musl"]
    System = Literal["Windows", "Darwin", "Linux"]
    ExeName = Literal["whitebox_tools.exe", "whitebox_tools"]


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
def _get_platform_suffix() -> tuple[System, Platform, ExeName]:
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
    exe_name = "whitebox_tools.exe" if system == "Windows" else "whitebox_tools"
    return system, suffix, exe_name


def _extract_wbt(zip_path: Path, wbt_root: Path, temp_path: Path, system: System) -> None:
    """Extract WhiteboxTools from zip file."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(path=temp_path)

        wbt_dir = next(temp_path.glob("WhiteboxTools*/WBT"), None)
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


@lru_cache(maxsize=1)
def _get_wbt_version(exe_path: str | Path) -> str:
    """Get the version of WhiteboxTools."""
    try:
        result = subprocess.run(
            [str(exe_path), "--version"], capture_output=True, text=True, check=True
        )
        match = re.search(r"WhiteboxTools v(\d+\.\d+\.\d+)", result.stdout.strip())
        return match.group(1) if match else "unknown"
    except (subprocess.CalledProcessError, OSError) as e:
        raise RuntimeError(f"Error running WhiteboxTools: {e!s}") from e


def _attempt_prepare_wbt(
    wbt_root: Path,
    zip_path: str | Path | None,
    refresh_download: bool,
) -> str | None:
    """Attempt to prepare WhiteboxTools once and return version or ``None`` if fails."""
    system, platform_suffix, exe_name = _get_platform_suffix()
    url = BASE_URL.format(system, platform_suffix)

    exe_path = wbt_root / exe_name
    if exe_path.exists() and not refresh_download:
        logger.info(f"Using existing WhiteboxTools executable: {exe_path}")
        try:
            return _get_wbt_version(exe_path)
        except RuntimeError as e:
            logger.warning(f"Existing executable is invalid: {e}")
            return None

    shutil.rmtree(wbt_root, ignore_errors=True)

    with TemporaryDirectory(prefix="wbt_", dir=".") as tmp:
        temp_path = Path(tmp)
        zip_path_local = temp_path / Path(url).name if zip_path is None else Path(zip_path)
        zip_path_local.parent.mkdir(parents=True, exist_ok=True)
        zip_path_local = zip_path_local.with_suffix(".zip")
        if refresh_download:
            zip_path_local.unlink(missing_ok=True)

        if not zip_path_local.exists():
            logger.info(f"Downloading WhiteboxTools from {url}")
            try:
                urllib.request.urlretrieve(url, zip_path_local)
            except urllib.error.URLError as e:
                logger.warning(f"Download failed: {e}")
                return None

        try:
            _extract_wbt(zip_path_local, wbt_root, temp_path, system)
            return _get_wbt_version(exe_path)
        except RuntimeError as e:
            logger.warning(f"Extraction failed: {e}")
            zip_path_local.unlink(missing_ok=True)
            shutil.rmtree(wbt_root, ignore_errors=True)
            return None


def prepare_wbt(
    wbt_root: str | Path,
    zip_path: str | Path | None = None,
    refresh_download: bool = False,
    max_attempts: int = 3,
) -> str:
    """Download the WhiteboxTools executable for the current platform.

    Parameters
    ----------
    wbt_root : str or Path
        Root directory to extract WhiteboxTools to.
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables, defaults to ``None``.
        If ``None``, the zip file will be downloaded to a temporary directory that gets
        deleted after the function finishes. Otherwise, the zip file will be saved to
        the specified path.
    refresh_download : bool, optional
        Whether to refresh the download even if WhiteboxTools is found.
        Defaults to ``False``.
    max_attempts : int, optional
        Maximum number of attempts to prepare WhiteboxTools, defaults to 3.

    Returns
    -------
    str
        Version of WhiteboxTools.
    """
    wbt_root = Path(wbt_root)
    wbt_root.mkdir(parents=True, exist_ok=True)
    lock_path = wbt_root / ".wbt_lock"

    # Acquire lock to allow only one process to prepare WhiteboxTools
    with SoftFileLock(lock_path):
        for attempt in range(max_attempts):
            version = _attempt_prepare_wbt(wbt_root, zip_path, refresh_download)
            if version:
                return version
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed, retrying...")

        raise RuntimeError(f"Failed to prepare WhiteboxTools after {max_attempts} attempts.")


def _run_wbt(
    exe_path: str | Path,
    tool_name: str,
    args: list[str],
    max_procs: int,
    compress_rasters: bool,
    work_dir: str | Path,
    version: str,
) -> None:
    """Run a WhiteboxTools command."""
    if tool_name in ("BreachDepressionsLeastCost", "breach_depressions_least_cost"):
        logger.warning("Forcing BreachDepressionsLeastCost to use a single process.")
        msg = " ".join(
            (
                "In WBT v2.4.0, BreachDepressionsLeastCost is unstable",
                ", for now, it is recommended to use BreachDepressions instead.",
                "For more information, see:\n",
                "https://github.com/jblindsay/whitebox-tools/issues/418\n",
                "https://github.com/jblindsay/whitebox-tools/issues/416\n",
                "https://github.com/jblindsay/whitebox-tools/issues/407\n",
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
        self,
        src_dir: Path,
        save_dir: Path,
        files_to_save: list[str] | tuple[str, ...] | None,
        version: str,
    ) -> None:
        self.src_dir = src_dir
        self.files_to_save = files_to_save
        if self.files_to_save is not None:
            self.files_to_save = list(self.files_to_save)
            # add .dbf, .prj, .shx files for Shapefile outputs
            for file in self.files_to_save:
                if file.endswith(".shp"):
                    stem = file[:-4]
                    self.files_to_save.extend([f"{stem}.dbf", f"{stem}.prj", f"{stem}.shx"])

        self.save_dir = save_dir
        self.version = version
        self.outputs = {}
        self.system, *_ = _get_platform_suffix()

    @staticmethod
    def _extract_outputs(wbt_args: dict[str, list[str]]) -> set[str]:
        """Extract output filenames from WhiteboxTools arguments."""
        outputs = []
        for args in wbt_args.values():
            output = [arg.split("=")[1] for arg in args if arg.startswith(("-o=", "--output"))]
            # add .dbf, .prj, .shx files for Shapefile outputs
            for out in output:
                if out.endswith(".shp"):
                    stem = out[:-4]
                    output.extend([f"{stem}.dbf", f"{stem}.prj", f"{stem}.shx"])
            outputs.extend(output)
        return set(outputs)

    def run(
        self,
        wbt_args: dict[str, list[str]],
        wbt_root: str | Path,
        compress_rasters: bool,
        max_procs: int,
    ) -> None:
        """Run WhiteboxTools operations.

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
        _, _, exe_name = _get_platform_suffix()
        exe_path = Path(wbt_root) / exe_name
        self.outputs = self._extract_outputs(wbt_args)
        for tool_name, args in wbt_args.items():
            _run_wbt(
                exe_path, tool_name, args, max_procs, compress_rasters, self.src_dir, self.version
            )

    def _cleanup(self) -> None:
        """Delete intermediate files and move output files to save_dir."""
        if self.save_dir != self.src_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            if self.files_to_save is not None:
                for file in self.files_to_save:
                    source = self.src_dir / file
                    if not source.exists():
                        logger.exception(f"Output file to save {source} not found")
                        raise FileNotFoundError(f"Output file to save {source} not found")
                    destination = Path(self.save_dir, file)
                    destination.unlink(missing_ok=True)
                    shutil.move(source, destination)
                    logger.info(f"Moved output file {source} to {destination}")
                _ = [(self.src_dir / f).unlink(missing_ok=True) for f in self.outputs]
                logger.info("Deleted remaining intermediate files.")
            else:
                for file in self.outputs:
                    out_file = Path(self.save_dir, file)
                    out_file.unlink(missing_ok=True)
                    shutil.move(self.src_dir / file, out_file)
        elif self.files_to_save is not None:
            for file in self.outputs:
                if file not in self.files_to_save:
                    Path(self.src_dir / file).unlink()
                    logger.info(f"Deleted intermediate file {file}")

    def __enter__(self) -> _WBTSession:  # noqa: PYI034
        logger.info(
            f"Starting WhiteboxTools session with source directory: {self.src_dir.absolute()}"
        )
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, *_
    ) -> bool:
        # If an exception occurred, propagate it
        if exc_type is not None:
            for file in self.outputs:
                Path(self.src_dir / file).unlink(missing_ok=True)
            logger.info("Deleted all intermediate files.")
            logger.exception(f"An error occurred: {exc_value}")
            return False
        self._cleanup()
        logger.info(
            f"Completed WhiteboxTools session with source directory: {self.src_dir.absolute()}"
        )
        return True


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
        Path to the source directory containing input files. This will be the working
        directory for the WhiteboxTools session. The input files should be in this directory.
        Thus, when using the files in this directory in ``arg_dict``, you must just use the
        filenames without the directory path. Refer to the example in ``arg_dict``.
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
        (default is ``"."``, i.e., current working directory).
    wbt_root : str or Path, optional
        Path to the directory the Whitebox executables will be extracted to
        (default is ``"WBT"``).
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables (default is ``None``).
        If ``None``, the zip file will be downloaded to a temporary directory that gets
        deleted after the function finishes. Otherwise, the zip file will be saved to
        the specified path.
    refresh_download : bool, optional
        Whether to refresh the download if WhiteboxTools is found (default is ``False``).
    compress_rasters : bool, optional
        Whether to compress output rasters (default is ``False``).
    max_procs : int, optional
        The maximum number of processes to use (default is ``-1``).
    verbose : bool, optional
        Whether to print verbose output (default is ``False``).

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

    version = prepare_wbt(wbt_root, zip_path, refresh_download)

    if not isinstance(arg_dict, dict) or not all(
        isinstance(k, str) and isinstance(v, (list, tuple)) for k, v in arg_dict.items()
    ):
        raise ValueError("arg_dict must be a dict of str keys and list or tuple values.")

    if not (files_to_save is None or isinstance(files_to_save, (list, tuple))):
        raise TypeError("files_to_save must be None, a list, or tuple of strings.")

    with _WBTSession(Path(src_dir), Path(save_dir), files_to_save, version) as wbt:
        wbt.run(arg_dict, wbt_root, compress_rasters, max_procs)


def _run_wbt_cmd(
    cmd: str, wbt_root: str | Path = "WBT", zip_path: str | Path | None = None
) -> CompletedProcess[str]:
    """Run WhiteboxTools command to list available tools and their options."""
    logger.setLevel(logging.WARNING)
    _ = prepare_wbt(wbt_root, zip_path, False)
    _, _, exe_name = _get_platform_suffix()
    exe_path = Path(wbt_root) / exe_name
    return subprocess.run([str(exe_path), cmd], capture_output=True, text=True, check=True)


def list_tools(wbt_root: str | Path = "WBT", zip_path: str | Path | None = None) -> dict[str, str]:
    """List the available WhiteboxTools commands.

    Parameters
    ----------
    wbt_root : str or Path, optional
        Path to the directory containing the WhiteboxTools executables
        (default is ``"WBT"``).
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables (default is ``None``).

    Returns
    -------
    dict
        A dictionary of WhiteboxTools commands and their descriptions. Can
        be converted to a ``pandas.Series`` for easier viewing using
        ``pd.Series(pywbt.list_tools())``.
    """
    result = _run_wbt_cmd("--listtools", wbt_root, zip_path)
    tools = (t.split(":") for t in result.stdout.strip().split("\n")[1:] if t)
    return {n: d.strip() for n, d in tools}


def tool_parameters(
    tool_name: str, wbt_root: str | Path = "WBT", zip_path: str | Path | None = None
) -> list[dict[str, str]]:
    """List the parameters for a WhiteboxTools command.

    Parameters
    ----------
    tool_name : str
        Name of the WhiteboxTools command.
    wbt_root : str or Path, optional
        Path to the directory containing the WhiteboxTools executables
        (default is ``"WBT"``).
    zip_path : str or Path, optional
        Path to the zip file containing the WhiteboxTools executables (default is ``None``).

    Returns
    -------
    list
        A list of WhiteboxTools command parameters and their descriptions.
        Can be converted to a ``pandas.DataFrame`` for easier viewing. For example,
        to get parameters of ``Aspect`` tool, use
        ``pd.DataFrame(pywbt.tool_parameters("Aspect"))``.
    """
    result = _run_wbt_cmd(f"--toolparameters={tool_name}", wbt_root, zip_path)
    return json.loads(result.stdout)["parameters"]
