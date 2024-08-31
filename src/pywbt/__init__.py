"""Top-level API for PyWBT."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pywbt.pywbt import whitebox_tools

try:
    __version__ = version("pywbt")
except PackageNotFoundError:
    __version__ = "999"

__all__ = ["whitebox_tools"]
