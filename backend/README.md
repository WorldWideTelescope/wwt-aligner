# The AAS WorldWide Telescope Sky Aligner: Backend Module

`wwt-aligner` is a tool to match RGB images (JPEGs, TIFFs, etc) to scientific
FITS images and annotate them with spatial information using AVM tags.

This portion of the source code implements the “backend”: the
`wwt-aligner-agent` command-line program and the tools to build a Docker
container that encapsulates it. This backend is driven by the “frontend”, a
small program that orchestrates to launching of the Docker app on a user
machine.

The `wwt-aligner` program is part of the [AAS WorldWide Telescope][wwt] system
and its development was sponsored by the [Space Telescope Science Institute][stsci].

[wwt]: https://worldwidetelescope.org/home/
[stsci]: https://www.stsci.edu/
