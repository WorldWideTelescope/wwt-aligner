# rc: minor bump

- Add support for the `wwt-aligner preview` command. This command includes some
  special plumbing to allow you to preview the WWT-formatted version of a
  processed image using your computer’s web browser.


# wwt-aligner-frontend 0.3.0 (2021-03-02)

- Lots of work towards trying to reach basic functionality.
- Making a release now to test out the GitHub pages deployment automation.


# wwt-aligner-frontend 0.2.1 (2021-01-15)

No code changes. Iterating on the deployment pipeline.


# wwt-aligner-frontend 0.2.0 (2021-01-15)

Initial test release of the WWT Aligner frontend, to see if we can correctly
publish our binaries to GitHub releases.

Eventually we could/should publish this as a crate to Cargo, but we don't expect
other crates to rely on this one, so it's not a priority.
