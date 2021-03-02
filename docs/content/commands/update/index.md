+++
title = "wwt-aligner update"
weight = 2100
+++

This command installs or updates the aligner tool implementation to the latest
released code.

# Synopsis

```
wwt-aligner update [--latest]
```

# Arguments

By default, this command will update the Aligner’s [Docker image] to the latest
stable software release. If the `--latest` option is provided, you’ll instead
get the most recent “bleeding edge” version provided by WWT. This can be useful
for beta-testing new features.

[Docker image]: https://docs.docker.com/engine/reference/commandline/images/

# Remarks

To “undo” an update to the “latest” version, just rerun this command without the
`--latest` argument. That will get you using the “stable” version again.
