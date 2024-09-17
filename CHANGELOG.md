# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[Unreleased\]

## \[0.2.1\] - 2024-09-17

### Added

- Make `files_to_save` optional in the `whitebox_tools` function. If not provided, all
    generated intermediate files will be stored in `save_dir` (default is the source
    directory).
- Improvements to documentation including writing, the look and feel of the
    documentations, and a new section for WBT workflows that can be found
    [here](https://pywbt.readthedocs.io/latest/workflows).

### Changed

- Avoid copying all files from the `src_dir` to the temporary directory,
    instead, run the tools in the `src_dir` itself. This change will
    avoid copying large files and could improve performance. With this change,
    all intermediate files will be stored in `src_dir` unless `files_to_save`
    is provided which will save only the specified output files and delete the
    rest of the intermediate files.
- Improve performance by extracting and copying the input files using
    `zipfile.ZipFile.extractall` and `shutil.copytree`.
- Improve the logic of determining the type of system platform by only calling
    `platform.system()` once and caching the result.
- Improve the writing of the documentation.

## \[0.2.0\] - 2024-09-2

### Highlights

This is a breaking change release. The `whitebox_tools` function now takes care of
running the tools in a temporary directory and saving the output files to a specified
directory. This change makes the function more user-friendly and easier to use.

### Changed

- Add two new arguments and remove one argument from the `whitebox_tools` function.
    The new arguments are:

    - `src_dir` (a `str` or `Path`): Path to the source directory containing the input files.
        All user input files will be copied from this directory to a temporary directory for
        processing. Note that when using these files in `arg_dict`, you should use the filenames
        without the directory path since the internal working directory of the WhitboxTools is
        set to the temporary directory where the files are copied.
    - `save_dir` (a `str` or `Path`): Path to the directory where the output files
        will be saved. If not provided, the output files will be saved in the source
        directory.
    - `files_to_save` (a `list` of `str`): List of output files to save to the `save_dir`.
        Note that these should be the filenames without the directory path, just as they are
        used in the `arg_dict`, i.e. the values that are passed by `-o` or `--output` in the
        WhiteboxTools command.

    The removed argument is:

    - `work_dir`: This argument is no longer needed since the working directory is set to
        the temporary directory where the input files are copied.

- All examples have been updated to reflect the changes in the `whitebox_tools` function.

### Added

- A new example notebooks has been added to compute Topographic Wetness Index (TWI) using
    PyWBT for a watershed in Houston, Texas.
- In the Delineate Basins notebook added a new plot for the mainstems.
- Added a new function to the `utils` module of the example notebooks to get DEM data from
    the USGS's 3D Elevation Program (3DEP).

## \[0.1.1\] - 2024-09-1

- This release has no changes, it is just to trigger the release process since
    the initial release on PyPi did not include the archive which is needed for
    `conda-forge` to build the package.

## \[0.1.0\] - 2024-08-31

- Initial release.
