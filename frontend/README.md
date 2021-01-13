# The AAS WorldWide Telescope Sky Aligner: Frontend Module

`wwt-aligner` is a tool to match RGB images (JPEGs, TIFFs, etc) to scientific
FITS images and annotate them with spatial information using AVM tags.

This portion of the source code implements the “frontend” `wwt-aligner`
command-line program, which is really just a small shim that delegates most of
the work to code that runs inside a Docker container.

The `wwt-aligner` program is part of the [AAS WorldWide Telescope][wwt] system
and its development was sponsored by the [Space Telescope Science Institute][stsci].

[wwt]: https://worldwidetelescope.org/home/
[stsci]: https://www.stsci.edu/
