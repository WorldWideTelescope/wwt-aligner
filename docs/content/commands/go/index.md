+++
title = "wwt-aligner go"
weight = 700
+++

This command runs one alignment, from start to finish.

# Synopsis

A typical invocation is:

```
wwt-aligner go
    -o {OUTPUT-PATH}
    {RGB-PATH}
    {FITS-PATH} [FITS-PATHS ...]
```

This command analyzes one or more FITS files (`FITS-PATH...`) to produce
[Astrometry.Net] “indices” giving the locations of stars on the sky, then finds
star-like sources in the input RGB image (`RGB-PATH`) and solves for their
alignment relative to the FITS files. A new output image (`OUTPUT-PATH`) is
created that augments the input image with [AVM] coordinate metadata.

[Astrometry.Net]: https://astrometry.net/
[AVM]: https://www.virtualastronomy.org/avm_metadata.php

For the time being, the output image must be in PNG or JPEG format because we
are currently unable to export AVM data to other formats. If the input image is
not in one of these formats, it will be converted.

# Detailed Usage

```
wwt-aligner go
    -o|--output {OUTPUT-PATH}
    [-t|--tile TILE-PATH]
    [-W|--workdir WORK-PATH]
    [--anet-bin-prefix PREFIX]
    {RGB-PATH}
    {FITS-PATH} [FITS-PATHS ...]
```

If the `-t TILE-PATH` option is provided, the output image will be “tiled” into
the [AAS WorldWide Telescope][wwt] format with the output files placed into the
new directory identified by the `TILE-PATH` argument. This directory will
include the tiled image data (a set of small PNG files) and an `index_rel.wtml`
[WTML] file containing the astrometric metadata. If you use this option, you can
then check your alignment in WWT by using the [wwt-aligner preview][cli-preview]
command:

[wwt]: https://worldwidetelescope.org/home
[WTML]: https://docs.worldwidetelescope.org/data-guide/1/data-file-formats/collections/
[cli-preview]: @/commands/preview/index.md

```sh
$ wwt-aligner go -o aligned.jpg -t tiled input.tif reference.fits
$ wwt-aligner preview tiled/index_rel.wtml
```

The `-W WORK-DIR` option causes the tool to save its working files in the
specified directory, as opposed to using a temporary directory. This can be
useful for low-level debugging of the alignment process.

The `--anet-bin-prefix` option can be ignored in almost all use cases. If you
are testing the agent outside of the Docker container, you can use it to tell
the agent where to find the Astrometry.Net programs.

The [generic command-line arguments](@/commands/_index.md#generic-command-line-arguments)
are also supported.

# Remarks

## FITS inputs

The aligner will make its best efforts to extract useful image data out of each
input FITS file that is passed to it. If it is unable to find such image data,
it will simply ignore that input FITS file. Please [file a bug][bug] if you have
an example FITS file that the aligner is unable to properly process.

[bug]: https://github.com/WorldWideTelescope/wwt-aligner/issues/new

# See Also

- [wwt-aligner preview][cli-preview]
