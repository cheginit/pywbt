# PyWBT: WhiteboxTools Wrapper for Python

[![PyPI](https://img.shields.io/pypi/v/pywbt)](https://pypi.org/project/pywbt/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/pywbt)](https://anaconda.org/conda-forge/pywbt)[![CI](https://github.com/cheginit/pywbt/actions/workflows/test.yml/badge.svg)](https://github.com/cheginit/pywbt/actions/workflows/test.yml)[![Documentation Status](https://readthedocs.org/projects/pywbt/badge/?version=latest)](https://pywbt.readthedocs.io/en/latest/?badge=latest)

## Features

PyWBT is a lightweight Python wrapper (only using Python's built-in modules) for
the command-line interface of [WhiteboxTools](https://www.whiteboxgeo.com/) (WBT),
a powerful Rust library for geospatial analysis. It is designed to simplify the use of WhiteboxTools by providing a Pythonic interface, allowing users to easily
run tools and create custom workflows.

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
function called `whitebox_tools` that can be used to run different tools.
Considering that WBT is a command-line tool, it can generate intermediate files.
A good practice for using PyWBT is to use Python's built-in `tempfile` module to
create a temporary directory that gets deleted after the execution of the tools and
only store the files that are necessary for further analysis. For example, if we
have a DEM file called `dem.tif` in the current directory, we can use the following
code to calculate the Strahler stream order:

```python
import tempfile
from pywbt import whitebox_tools


with tempfile.TemporaryDirectory(dir=".") as work_dir:
    shutil.copy("dem.tif", work_dir)
    wbt_args = {
        "BreachDepressions": ["dem.tif", "--fill_pits", "-o=dem_corr.tif"],
        "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
        "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
        "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
        "StrahlerStreamOrder": ["--d8_pntr=fdir.tif", "--streams=streams.tif", "-o=strahler.tif"],
    }
    whitebox_tools(wbt_args, work_dir=work_dir)
    shutil.copy(Path(work_dir) / "strahler.tif", "strahler.tif")
```

![straher](https://raw.githubusercontent.com/cheginit/pywbt/main/docs/examples/stream_order.png)

For more information about the `whitebox_tools` function and its arguments, please
visit the [API Reference](https://pywbt.readthedocs.io/en/latest/reference/#pywbt.pywbt.whitebox_tools).
Additionally, for more information on different tools that WBT offers and their
arguments, please visit its
[documentation](https://www.whiteboxgeo.com/manual/wbt_book/).

## Contributing

Contributions are welcome! For more information on how to contribute to PyWBT,
please see the [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) files.

## License

PyWBT is licensed under the MIT License. For more information, please see the
[LICENSE](LICENSE) file.
