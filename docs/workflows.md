# Workflows

Here are some useful workflows for geospatial operations using WhiteboxTools and PyWBT.
You can copy-paste and customize these workflows into your Python script and pass them to the
`arg_dict` argument of `pywbt.whitebox_tools` function.

Contributing to this list is highly appreciated. You can just click on the `Edit this page` link at the top right of this page.

## Topographic Wetness Index

```py
{
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8FlowAccumulation": [
        "-i=dem_corr.tif",
        "--out_type='specific contributing area'",
        "-o=sca.tif",
    ],
    "Slope": ["-i=dem_corr.tif", "--units=degrees", "-o=slope.tif"],
    "WetnessIndex": ["--sca=sca.tif", "--slope=slope.tif", "-o=twi.tif"],
}
```

## Basin Delineation

```py
{
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "Basins": ["--d8_pntr=fdir.tif", "-o=basins.tif"],
}
```

## Extract Streams

```py
{
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8FlowAccumulation": ["-i=dem_corr.tif", "-o=d8accum.tif"],
    "ExtractStreams": ["--flow_accum=d8accum.tif", "--threshold=600.0", "-o=streams.tif"],
}
```

## Find Mainstems

```py
{
    "BreachDepressions": ["-i=dem.tif", "--fill_pits", "-o=dem_corr.tif"],
    "D8Pointer": ["-i=dem_corr.tif", "-o=fdir.tif"],
    "D8FlowAccumulation": ["-i=fdir.tif", "--pntr", "-o=d8accum.tif"],
    "FindMainStem": ["--d8_pntr=fdir.tif", "--streams=d8accum.tif", "-o=mainstem.tif"],
}
```
