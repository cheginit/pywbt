# PyWBT: WhiteboxTools Wrapper for Python

[![PyPI](https://img.shields.io/pypi/v/pywbt)](https://pypi.org/project/pywbt/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/pywbt)](https://anaconda.org/conda-forge/pywbt)[![CI](https://github.com/cheginit/pywbt/actions/workflows/test.yml/badge.svg)](https://github.com/cheginit/pywbt/actions/workflows/test.yml)[![Documentation Status](https://readthedocs.org/projects/pywbt/badge/?version=latest)](https://pywbt.readthedocs.io/en/latest/?badge=latest)

## Features

PyWBT is a Python wrapper for the
[WhiteboxTools](https://www.whiteboxgeo.com/) command-line
interface. It is designed to simplify the use of WhiteboxTools, a powerful library
for geospatial analysis, in Python. PyWBT provides a Pythonic interface to
WhiteboxTools, allowing users to easily run tools, access tool metadata, and create
custom workflows.

## Installation

PyWBT can be installed using `pip`:

```bash
pip install pywbt
```

or `micromamba` (`conda` or `mamba` can also be used):

```bash
micromamba install -c conda-forge pywbt
```

## Usage

PyWBT provides a simple interface to WhiteboxTools. There is just a single
function called `whitebox_tools` that can be used to run tools. Here is an
example of how to use PyWBT to run several tools:

```python
wbt_args = {
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
    "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    "FindMainStem": ["--d8_pntr=fdir.tif", "--streams=d8accum.tif", "-o=mainstem.tif"],
    "StrahlerStreamOrder": ["--d8_pntr=fdir.tif", "--streams=streams.tif", "-o=strahler.tif"],
}
whitebox_tools(wbt_args)
```

![straher](https://raw.githubusercontent.com/cheginit/pywbt/main/docs/examples/stream_order.png)

For more information on how to different WhiteboxTools tools and their
arguments, please visit its
[documentation](https://www.whiteboxgeo.com/manual/wbt_book/).
