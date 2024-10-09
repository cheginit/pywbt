"""Configuration for pytest."""

from __future__ import annotations

import builtins
import contextlib
import importlib
import platform
import shutil
import tempfile
from typing import Any, Callable

import pytest


@pytest.fixture(autouse=True)
def add_doctest_imports(doctest_namespace: dict[str, object]) -> None:  # noqa: PT004
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


@pytest.fixture
def wrong_wbt_zipfile() -> str:
    """Determine the platform suffix for downloading WhiteboxTools."""
    system = platform.system()
    base_name = "WhiteboxTools_{}.zip"
    if system not in ("Windows", "Darwin", "Linux"):
        raise ValueError(f"Unsupported operating system: {system}")

    if system == "Windows":
        suffix = "darwin_amd64"
    elif system == "Darwin":
        suffix = "linux_amd64"
    else:
        suffix = "win_amd64"
    return base_name.format(suffix)


@pytest.fixture
def block_optional_imports(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    def _block(*names: str) -> None:
        original_import = builtins.__import__

        def mocked_import(name: str, *args: Any, **kwargs: Any):
            if name in names:
                raise ImportError(f"Import of '{name}' is blocked for testing")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mocked_import)
        monkeypatch.setattr(importlib, "import_module", mocked_import)

    return _block


@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_", dir=".")
    yield temp_dir
    with contextlib.suppress(PermissionError):
        shutil.rmtree(temp_dir)


@pytest.fixture
def wbt_args() -> dict[str, list[str]]:
    return {
        "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    }
