"""Command-line interface for pywbt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pywbt.pywbt import whitebox_tools


def main():
    parser = argparse.ArgumentParser(
        description="Run WhiteboxTools using a TOML configuration file.",
    )
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    parser.add_argument("config_file", type=Path, help="Path to the TOML configuration file.")
    cfg = Path(parser.parse_args().config_file)
    if not cfg.exists():
        raise FileNotFoundError(f"File not found: {cfg}")

    try:
        with cfg.open("rb") as f:
            config = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML file: {e}") from e

    src_dir = config.get("src_dir")
    arg_dict = config.get("arg_dict")
    files_to_save = config.get("files_to_save")
    save_dir = config.get("save_dir", ".")
    wbt_root = config.get("wbt_root", "WBT")
    compress_rasters = config.get("compress_rasters", False)
    zip_path = config.get("zip_path")
    refresh_download = config.get("refresh_download", False)
    max_procs = config.get("max_procs", -1)
    verbose = config.get("verbose", False)

    if not src_dir or not isinstance(arg_dict, dict):
        raise ValueError("The TOML file must define 'src_dir' and 'arg_dict'.")

    whitebox_tools(
        src_dir=src_dir,
        arg_dict=arg_dict,
        files_to_save=files_to_save,
        save_dir=save_dir,
        wbt_root=wbt_root,
        compress_rasters=compress_rasters,
        zip_path=zip_path,
        refresh_download=refresh_download,
        max_procs=max_procs,
        verbose=verbose,
    )
