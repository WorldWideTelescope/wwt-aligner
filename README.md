# The AAS WorldWide Telescope Sky Aligner

The [WWT] aligner is a tool to match RGB images (JPEGs, TIFFs, etc) to
scientific FITS images and annotate them with spatial information using AVM
tags.

[WWT]: https://worldwidetelescope.org/home/

The core image-matching algorithm uses the [Astrometry.net][anet] solver. The
WWT Aligner bundles this complex software system inside a [Docker] container and
provides a small “frontend” command-line tool, `wwt-aligner`, that launches it.

[anet]: https://astrometry.net/
[Docker]: https://www.docker.com/


## Installation and Documentation

Installation instructions may be found here:

> https://docs.worldwidetelescope.org/aligner/latest/installation/

The main documentation may be [found here][docs].

[docs]: https://docs.worldwidetelescope.org/aligner/latest/


## Acknowledgments

The development of `wwt-aligner` was sponsored by the Space Telescope Science
Institute.

The AAS WorldWide Telescope (WWT) system is a [.NET Foundation][dnf] project
brought to you by the [American Astronomical Society][aas] (AAS). Work on WWT
has been supported by those organizations, the [National Science
Foundation][nsf], the [Gordon and Betty Moore Foundation][moore], and
[Microsoft][msft]. For more information see [the WWT
Acknowledgments][acknowledgments].

[dnf]: https://dotnetfoundation.org/
[aas]: https://aas.org/
[nsf]: https://www.nsf.gov/
[moore]: https://www.moore.org/
[msft]: https://microsoft.com/
[acknowledgments]: https://worldwidetelescope.org/about/acknowledgments/
