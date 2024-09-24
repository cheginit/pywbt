"""Top-level API for PyWBT."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pywbt import dem_utils
from pywbt.pywbt import list_tools, tool_parameters, whitebox_tools

try:
    __version__ = version("pywbt")
except PackageNotFoundError:
    __version__ = "999"

__all__ = ["whitebox_tools", "list_tools", "tool_parameters", "dem_utils"]
