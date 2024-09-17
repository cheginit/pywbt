# PyWBT: WhiteboxTools Wrapper for Python

[![PyPI](https://img.shields.io/pypi/v/pywbt)](https://pypi.org/project/pywbt/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/pywbt)](https://anaconda.org/conda-forge/pywbt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/cheginit/pywbt/HEAD?labpath=docs%2Fexamples)

[![codecov](https://codecov.io/gh/cheginit/pywbt/graph/badge.svg?token=U2638J9WKM)](https://codecov.io/gh/cheginit/pywbt)
[![CI](https://github.com/cheginit/pywbt/actions/workflows/test.yml/badge.svg)](https://github.com/cheginit/pywbt/actions/workflows/test.yml)
[![Documentation Status](https://readthedocs.org/projects/pywbt/badge/?version=latest)](https://pywbt.readthedocs.io/latest/?badge=latest)

## Features

PyWBT is a lightweight Python wrapper for the command-line interface of
[WhiteboxTools](https://www.whiteboxgeo.com/) (WBT), a powerful Rust library for
geospatial analysis. Designed to simplify the use of WhiteboxTools, PyWBT provides a
Pythonic interface that enables users to easily run tools and create custom workflows.
Notably, PyWBT relies solely on Python's built-in modules, ensuring a minimal
dependency footprint.

Try PyWBT in your browser by clicking on the Binder badge above.

## Installation

You can install PyWBT using either `pip` or `micromamba`:

Using `pip`:

```bash
pip install pywbt
```

Using `micromamba` (or `conda`/`mamba`):

```bash
micromamba install -c conda-forge pywbt
```

## Usage

PyWBT offers a streamlined interface to WhiteboxTools (WBT) through a single function
called `whitebox_tools`. This function executes user-provided WBT workflows in a
temporary directory, saving only the specified output files rather than all intermediate
files. It handles downloading the WBT executable for the user's operating system, setting
up the environment, and running the tools.

The `whitebox_tools` function has several arguments, with two being mandatory and the rest
optional. The two required arguments are:

1. `src_dir`: Path to the source directory containing input files. All user input files
    are copied from this directory to a temporary directory for processing.

1. `arg_dict`: A dictionary with tool names as keys and lists of each tool's arguments
    as values. Input and output filenames should be specified without directory paths.

For example workflows using `arg_dict` to perform geospatial operations, refer to the
[Workflows](https://pywbt.readthedocs.io/latest/workflows/) section of the documentation. We
encourage users to contribute to this section by providing sequences of geospatial operations
for performing specific tasks, helping to build a comprehensive resource for the community.

Note that by default, all generated intermediate files will be stored in `save_dir` (default
is the current working directory). To save only the specified output files and delete the rest of
intermediate files, use the `files_to_save` argument to specify the list of target outputs. This list
should contain the filenames only specified without directory paths (as used in `arg_dict`).

Here's an example demonstrating how to use PyWBT to run a WBT workflow:

```python
import pywbt
from pathlib import Path

fname = Path("path/to/input_files/dem.tif")
wbt_args = {
    "BreachDepressions": [f"-i={fname.name}", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
    "ExtractStreams": [
        "--flow_accum=d8accum.tif",
        "--threshold=600.0",
        "-o=streams.tif",
    ],
    "FindMainStem": ["--d8_pntr=fdir.tif", "--streams=d8accum.tif", "-o=mainstem.tif"],
    "StrahlerStreamOrder": [
        "--d8_pntr=fdir.tif",
        "--streams=streams.tif",
        "-o=strahler.tif",
    ],
    "Basins": ["--d8_pntr=fdir.tif", "-o=basins.tif"],
}
pywbt.whitebox_tools(
    fname.parent, wbt_args, ("strahler.tif", "mainstem.tif", "basins.tif")
)
```

![Strahler Stream Order](https://raw.githubusercontent.com/cheginit/pywbt/main/docs/examples/images/stream_order.png)

For more examples, please visit PyWBT's [documentation](https://pywbt.readthedocs.io). For
detailed information about the `whitebox_tools` function and its arguments, refer to the
[API Reference](https://pywbt.readthedocs.io/latest/reference/#pywbt.pywbt.whitebox_tools).
Additionally, for comprehensive information on the various tools offered by WBT and their
arguments, consult its [documentation](https://www.whiteboxgeo.com/manual/wbt_book/).

## Contributing

Contributions to PyWBT are welcome! For more information on how to contribute, please refer
to the [CONTRIBUTING.md](https://pywbt.readthedocs.io/latest/CONTRIBUTING) and
[CODE_OF_CONDUCT.md](https://github.com/cheginit/pywbt/blob/main/CODE_OF_CONDUCT.md) files.

## License

PyWBT is licensed under the MIT License. For more details, please see the
[LICENSE](https://github.com/cheginit/pywbt/blob/main/LICENSE) file.
