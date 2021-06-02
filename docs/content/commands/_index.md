+++
title = "Command Reference"
sort_by = "weight"
insert_anchor_links = "right"
weight = 500
+++

This section provides reference documentation for the different sub-commands
provided by the `wwt-aligner` command-line program.

- [wwt-aligner go](@/commands/go/index.md) — do one alignment, start-to-finish
- [wwt-aligner preview](@/commands/preview/index.md) — preview a solved image in WWT
- [wwt-aligner update](@/commands/update/index.md) — update the implementation Docker image


# Generic Command-Line Arguments

All aligner commands support the following arguments:

#### `--log={LOGLEVEL}`

Set the level of logging detail. If unspecified or if `LOGLEVEL` is `default`,
standard messages are printed out. If `info`, “logging mode” will be activated:
messages will be printed out with timestamps, and the logging output will be
directed to the standard error stream rather than standard output. If `debug`,
logging mode will be activated and lots of debugging information will be
printed. If `warning`, logging mode will be activated but only warnings and
error messages will be printed.
