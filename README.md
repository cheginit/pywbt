# PyWBT: WhiteboxTools Wrapper for Python

[![PyPI](https://img.shields.io/pypi/v/pywbt)](https://pypi.org/project/pywbt/)
[![Conda](https://img.shields.io/conda/vn/conda-forge/pywbt)](https://anaconda.org/conda-forge/pywbt)[![CI](https://github.com/cheginit/pywbt/actions/workflows/test.yml/badge.svg)](https://github.com/cheginit/pywbt/actions/workflows/test.yml)[![codecov](https://codecov.io/gh/cheginit/pywbt/graph/badge.svg?token=U2638J9WKM)](https://codecov.io/gh/cheginit/pywbt)[![Documentation Status](https://readthedocs.org/projects/pywbt/badge/?version=latest)](https://pywbt.readthedocs.io/en/latest/?badge=latest)

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
This function has three required arguments:

1. `src_dir` (a `str` or `Path`):
Path to the source directory containing the input files. All user input files
will be copied from this directory to a temporary directory for processing.
Note that when using these files in ``arg_dict``, you should use the filenames
without the directory path since they the internal working directory of the
WhitboxTools is set to the temporary directory where the files are copied.

2. `arg_dict` (a `dict`):
A dictionary containing the tool names as keys and list of each
tool's arguments as values. For example:

``` py
{
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
}
```

Note that the input and output file names should not contain the directory path,
only the file names.

3. `files_to_save` (a `list` of `str`):
List of output files to save to the save_dir. Note that these should be the filenames
without the directory path, just as they are used in the ``arg_dict``, i.e. the
values that are passed by ``-o`` or ``--output`` in the WhiteboxTools command.

Let's see an example of how to use PyWBT to run a simple workflow:

``` py
import pywbt

fname = Path("path/to/input_files/dem.tif")
wbt_args = {
    "BreachDepressions": [f"-i={fname.name}", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
    "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
    "FindMainStem": ["--d8_pntr=fdir.tif", "--streams=d8accum.tif", "-o=mainstem.tif"],
    "StrahlerStreamOrder": ["--d8_pntr=fdir.tif", "--streams=streams.tif", "-o=strahler.tif"],
    "Basins": ["--d8_pntr=fdir.tif", "-o=basins.tif"],
}
pywbt.whitebox_tools(fname.parent, wbt_args, ("strahler.tif", "mainstem.tif", "basins.tif"))
```

![strahler](https://raw.githubusercontent.com/cheginit/pywbt/main/docs/examples/images/stream_order.png)

For more examples, please visit PyWBT's [documentation](https://pywbt.readthedocs.io)
and for more information about the `whitebox_tools` function and its arguments, please
visit the
[API Reference](https://pywbt.readthedocs.io/en/latest/reference/#pywbt.pywbt.whitebox_tools).
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
