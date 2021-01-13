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


## Installation

Instructions to come.


## Acknowledgments

The development of `wwt-aligner` was sponsored by the Space Telescope Science
Institute.

The AAS WorldWide Telescope (WWT) system is a [.NET Foundation][dnf] project.
Work on WWT and pywwt has been supported by the [American Astronomical
Society][aas] (AAS), the US [National Science Foundation][nsf] (grants [1550701]
and [1642446]), the [Gordon and Betty Moore Foundation][moore], and
[Microsoft][msft].

[nsf]: https://www.nsf.gov/
[1550701]: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1550701
[1642446]: https://www.nsf.gov/awardsearch/showAward?AWD_ID=1642446
[moore]: https://www.moore.org/
[msft]: https://microsoft.com/
