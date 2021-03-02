# wwt_aligner 0.4.1 (2021-03-02)

- Use portable compiler flags for the Docker build, so that the resulting image
  will run on a wide range of host systems. Astrometry.Net's build system
  reasonably defaults to aggressively tuning for the build host, but that's not
  the right choice for a Docker image.

# wwt_aligner 0.4.0 (2021-03-02)

Prototype release that might actually be functional. Mainly testing the
tweaked Docker deployment automation, though.

# wwt_aligner 0.3.1 (2021-01-15)

No code changes, trying Docker deployment again.

# wwt_aligner 0.3.0 (2021-01-15)

No code changes, trying Docker deployment again.

# wwt_aligner 0.2.0 (2021-01-15)

No code changes, trying Docker deployment again.

# wwt_aligner 0.1.0 (2021-01-15)

Initial prototype release. Note that our release artifact is the built Docker
image, not the Python module. For the time being we're not even publishing the
Python module to PyPI.
