"""Configuration for pytest."""

from __future__ import annotations

import platform

import pytest


@pytest.fixture(autouse=True)
def _add_standard_imports(doctest_namespace):
    """Add pywbt namespace for doctest."""
    import pywbt

    doctest_namespace["pywbt"] = pywbt


@pytest.fixture
def wbt_zipfile() -> str:
    """Determine the platform suffix for downloading WhiteboxTools."""
    system = platform.system()
    base_name = "WhiteboxTools_{}.zip"
    if system not in ("Windows", "Darwin", "Linux"):
        raise ValueError(f"Unsupported operating system: {system}")

    if system == "Windows":
        suffix = "win_amd64"
    elif system == "Darwin":
        suffix = "darwin_m_series" if platform.machine() == "arm64" else "darwin_amd64"
    else:
        suffix = "linux_musl" if "musl" in platform.libc_ver()[0].lower() else "linux_amd64"
    return base_name.format(suffix)
