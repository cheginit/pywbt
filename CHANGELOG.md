# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Fixed

### Changed

## [0.2.9] - 2025-02-18

### Added

- For `dem_utils.get_3dep` use `seamless-3dep` package to support any resolution not
    only 10, 30, and 60 meters. This Python library is more performant and caches
    downloaded intermediate files to avoid downloading the same files multiple times.
    This change requires adding optional `seamless-3dep` as a new dependency for the
    `dem_utils` module.
- For `dem_utils.get_nasadem` use `tiny-retriever` package for a more performant and
    reliable way to download the NASADEM data. Similarly, it caches downloaded
    intermediate files to avoid downloading the same files multiple times. This change
    requires adding `tiny-retriever` as a optional new dependency for the `dem_utils`
    module.

### Fixed

- In `whitebox_tools` function when `files_to_save` is not provided, before moving the
    output files to `save_dir`, check if the output files already exist in the
    `save_dir` and remove them before moving the new output files. This is to avoid an
    issue with `shutil.move` which fails to overwrite existing files.

## [0.2.8] - 2025-01-09

This release adds `filelock` as a dependency and `tomli` as an optional dependency.

### Added

- Add a command line interface to allow invoking `pywbt` from the command line. It only
    requires specifying path to a configuration file written in TOML format. This adds
    `tomli` as a new optional dependency for parsing the TOML configuration file if
    Python version is less than 3.11. Otherwise, Python's built-in `tomllib` module is
    used to parse the configuration file.An example configuration file can be found
    [here](https://raw.githubusercontent.com/cheginit/pywbt/main/tests/config.toml).

    ```bash
    pywbt path/to/config.toml
    ```

- Make `prepare_wbt` public so users can run this function once to download the WBT
    executable and then use the `whitebox_tools` function to run the tools. This can
    help avoid downloading the WBT executable multiple times when running `pywbt` in
    parallel or in different scripts.

- Use `filelock` library so only one instances of `prepare_wbt` can download the WBT
    executable at a time. This is to avoid race conditions when multiple processes try
    to setup the WBT executable at the same time.

## [0.2.7] - 2024-10-31

### Fixed

- Fix an issue when a Shapefile exists as input or output in the `arg_dict`. The issue
    would have caused an infinite loop when trying to copy the Shapefile and its
    auxiliary files. ({{ issue(3) }})

## [0.2.6] - 2024-10-09

### Fixed

- Fix a bug in extracting WBT executable from the zip file. The bug impacted mostly
    users who run PyWBT on cluster environments where the `tempfile` modules uses
    system's temporary directory which in most cases is not reliable. The fix is to use
    the `tempfile.TemporaryDirectory` context manager to create a temporary directory in
    the current working directory.

## [0.2.5] - 2024-10-08

### Fixed

- Automatically add auxiliary files of Shapefile when they exist in `arg_dict`. This
    ensures that the auxiliary files are also stored to `save_dir` when `files_to_save`
    is provided.

## [0.2.4] - 2024-09-24

### Added

- Add a new module called `dem_utils` that contains utilities for downloading and
    reading DEM data from 3DEP and NASADEM. Note that the module has some additional
    dependencies that need to be installed. To install these dependencies, use:

```bash
pip install pywbt[dem]
```

or using `micromamba`:

```bash
micromamba install -c conda-forge pywbt 'geopandas-base>=1' planetary-computer pystac-client rioxarray
```

## [0.2.3] - 2024-09-19

### Added

- When an exception occurs during running WBT, propagate the exception and clean up
    before existing.
- If for some reason simply running WBT fails, redownload the WBT executable and try
    again. This is to avoid the situation where the WBT executable is corrupted or not
    downloaded properly or is not compatible with the system platform.
- Add two new helper function that can be used to get the list of available tools, their
    respective descriptions and parameters: `list_tools` and `tool_parameters`. For
    better viewing and querying the outputs of these two functions, it is recommended to
    use the `pandas` library. For example, you can use `pd.Series(pywbt.list_tools())`
    to get a `pandas.Series` of the available tools, and
    `pd.DataFrame(pywbt.tool_parameters("BreachDepressions"))` to get a
    `pandas.DataFrame` of the parameters for the `BreachDepressions` tool.

## [0.2.2] - 2024-09-17

### Added

- Make `files_to_save` optional in the `whitebox_tools` function. If not provided, all
    generated intermediate files will be stored in `save_dir` (default is the source
    directory).
- Improvements to documentation including writing, the look and feel of the
    documentations, and a new section for WBT workflows that can be found
    [here](https://pywbt.readthedocs.io/latest/workflows).

### Changed

- Avoid copying all files from the `src_dir` to the temporary directory, instead, run
    the tools in the `src_dir` itself. This change will avoid copying large files and
    could improve performance. With this change, all intermediate files will be stored
    in `src_dir` unless `files_to_save` is provided which will save only the specified
    output files and delete the rest of the intermediate files.
- Improve performance by extracting and copying the input files using
    `zipfile.ZipFile.extractall` and `shutil.copytree`.
- Improve the logic of determining the type of system platform by only calling
    `platform.system()` once and caching the result.
- Improve the writing of the documentation.

## [0.2.0] - 2024-09-2

### Highlights

This is a breaking change release. The `whitebox_tools` function now takes care of
running the tools in a temporary directory and saving the output files to a specified
directory. This change makes the function more user-friendly and easier to use.

### Changed

- Add two new arguments and remove one argument from the `whitebox_tools` function. The
    new arguments are:

    - `src_dir` (a `str` or `Path`): Path to the source directory containing the input
        files. All user input files will be copied from this directory to a temporary
        directory for processing. Note that when using these files in `arg_dict`, you
        should use the filenames without the directory path since the internal working
        directory of the WhitboxTools is set to the temporary directory where the files
        are copied.
    - `save_dir` (a `str` or `Path`): Path to the directory where the output files will be
        saved. If not provided, the output files will be saved in the source directory.
    - `files_to_save` (a `list` of `str`): List of output files to save to the `save_dir`.
        Note that these should be the filenames without the directory path, just as they
        are used in the `arg_dict`, i.e. the values that are passed by `-o` or `--output`
        in the WhiteboxTools command.

    The removed argument is:

    - `work_dir`: This argument is no longer needed since the working directory is set to
        the temporary directory where the input files are copied.

- All examples have been updated to reflect the changes in the `whitebox_tools`
    function.

### Added

- A new example notebooks has been added to compute Topographic Wetness Index (TWI)
    using PyWBT for a watershed in Houston, Texas.
- In the Delineate Basins notebook added a new plot for the mainstems.
- Added a new function to the `utils` module of the example notebooks to get DEM data
    from the USGS's 3D Elevation Program (3DEP).

## [0.1.1] - 2024-09-1

- This release has no changes, it is just to trigger the release process since the
    initial release on PyPi did not include the archive which is needed for
    `conda-forge` to build the package.

## [0.1.0] - 2024-08-31

- Initial release.
