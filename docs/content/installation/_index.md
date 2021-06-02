+++
title = "Installation"
sort_by = "weight"
insert_anchor_links = "right"
weight = 100
+++

Installing the WWT Aligner is a two-step process.


# Prerequisites

The WWT Aligner bundles up the complex [Astrometry.Net] software system using
the [Docker] “containerization” system. In order to use the WWT Aligner, you
must first [install Docker].

[Astrometry.Net]: https://astrometry.net/
[Docker]: https://www.docker.com/
[install Docker]: https://docs.docker.com/get-docker/


# Install the Frontend

Once you’ve got Docker, you should install the “frontend” component, which is a
small program that talks to your Docker installation.

You can download the latest release of the frontend from GitHub [by following
this link][latest]. Each release is published with versions of the frontend
compiled for different operating systems.

[latest]: https://worldwidetelescope.github.io/wwt-aligner/latest-release/

To install the frontend, download the appropriate archive for your OS and unpack
it. For instance, on a Mac you’ll want to download the file with the name
looking like `wwt-aligner-frontend-<VERSION>-x86_64-apple-darwin.tar.gz`. This
tarball will unpack to a single file, `wwt-aligner`.

Put this file in a place where it can be found by your computer’s command-line
prompt. On many systems, a reasonable default is the `/usr/local/bin` directory.
You can set this up on the command line with:

```sh
$ sudo mv wwt-aligner /usr/local/bin/
```

You will know that this stage of the installation is successful when you can run
the command `wwt-aligner` from your command line prompt and get some program
usage help printed.


# Download the Backend

The final step is to download the bundled software in the form of a Docker
“image”. The frontend can do this for you. Run:

```sh
$ wwt-aligner update
```

The image is about 500 megabytes in size, so it may take a little while to
download. But once that’s done, you are ready to align some images!
