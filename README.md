# PyWBT: Python Wrapper for WhiteboxTools

[![PyPI](https://img.shields.io/pypi/v/pywbt)](https://pypi.org/project/pywbt/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/pywbt)](https://anaconda.org/conda-forge/pywbt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/cheginit/pywbt/HEAD?labpath=docs%2Fexamples)

[![codecov](https://codecov.io/gh/cheginit/pywbt/graph/badge.svg?token=U2638J9WKM)](https://codecov.io/gh/cheginit/pywbt)
[![CI](https://github.com/cheginit/pywbt/actions/workflows/test.yml/badge.svg)](https://github.com/cheginit/pywbt/actions/workflows/test.yml)
[![Documentation Status](https://readthedocs.org/projects/pywbt/badge/?version=latest)](https://pywbt.readthedocs.io/latest/?badge=latest)

## Overview

**PyWBT** is a Python wrapper for the [WhiteboxTools](https://www.whiteboxgeo.com/) (WBT)
geospatial analysis library. It simplifies geospatial workflows by providing an easy-to-use
Pythonic interface while maintaining a minimal dependency footprint—relying only on Python's
built-in modules.

You can try PyWBT directly in your browser by clicking the Binder badge above.

## Key Features

- Lightweight Python interface for WBT’s command-line tools.
- Seamless integration with WBT for custom geospatial workflows.
- Minimal dependencies for ease of installation.
- Optional `dem_utils` module for obtaining and preprocessing DEM data from [3DEP](https://www.usgs.gov/3d-elevation-program) (US only at 10, 30, and 60 m resolutions) and [NASADEM](https://planetarycomputer.microsoft.com/dataset/nasadem) (global coverage at 30 m resolution).

## Installation

Install PyWBT via `pip` or `micromamba`:

Using `pip`:

```bash
pip install pywbt
```

Using `micromamba` (or `conda`/`mamba`):

```bash
micromamba install -c conda-forge pywbt
```

## Quick Start

PyWBT enables the execution of WBT tools with the `whitebox_tools` function, which manages the
environment setup, including downloading the WBT executable for your operating system.

### Basic Usage

The `whitebox_tools` function requires two key arguments:

- `src_dir`: Directory containing the input files.
- `arg_dict`: Dictionary where tool names are keys and argument lists are values.

Example usage:

```python
import pywbt
from pathlib import Path

src_dir = Path("path/to/input_files/")
wbt_args = {
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    # Additional tools...
}

pywbt.whitebox_tools(src_dir, wbt_args)
```

For more detailed workflows and usage patterns, refer to the
[documentation](https://pywbt.readthedocs.io/latest/workflows).

### Managing Output Files

To manage the output, specify which intermediate files to keep using the `files_to_save` argument.
Only those files listed will be saved, and the rest will be deleted. By default, all files are
stored in `save_dir` (the current working directory, by default).

### Tool Lookup

Use `list_tools` and `tool_parameters` to explore available tools and their arguments. Here's an
example using `pandas` for querying tools:

```python
import pandas as pd

tools = pd.Series(pywbt.list_tools())
tools[tools.str.contains("depression", case=False)]
```

Get parameters for a specific tool:

```python
pd.DataFrame(pywbt.tool_parameters("BreachDepressions"))
```

### DEM Utilities

The `dem_utils` module supports downloading and reading DEM data from 3DEP and NASADEM. Install
optional dependencies for DEM utilities:

```bash
pip install pywbt[dem]
```

Or using `micromamba`:

```bash
micromamba install -c conda-forge pywbt 'geopandas-base>=1' planetary-computer pystac-client rioxarray
```

## Example Workflow

We can delineate the stream network and calculate the Strahler stream order for a
region in London using PyWBT, as shown below:

```python
import pywbt
from pathlib import Path

bbox = (0.0337, 51.5477, 0.1154, 51.6155)
src_dir = Path("path/to/input_files/")
pywbt.dem_utils.get_nasadem(bbox, src_dir / "dem.tif", to_utm=True)
wbt_args = {
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
    "ExtractStreams": [
        "--flow_accum=d8accum.tif",
        "--threshold=600.0",
        "-o=streams.tif",
    ],
    "StrahlerStreamOrder": [
        "--d8_pntr=fdir.tif",
        "--streams=streams.tif",
        "--zero_background",
        "-o=strahler.tif",
    ],
}
pywbt.whitebox_tools(src_dir, wbt_args)
```

![Strahler Stream Order](https://raw.githubusercontent.com/cheginit/pywbt/main/docs/examples/images/stream_order.png)

For more examples, visit the [documentation](https://pywbt.readthedocs.io).

## Contributing

We welcome contributions! For guidelines, please refer to the [CONTRIBUTING.md](https://pywbt.readthedocs.io/latest/CONTRIBUTING) and [CODE_OF_CONDUCT.md](https://github.com/cheginit/pywbt/blob/main/CODE_OF_CONDUCT.md).

## License

PyWBT is licensed under the MIT License. See the [LICENSE](https://github.com/cheginit/pywbt/blob/main/LICENSE) file for details.
