// Copyright 2020-2021 the .NET Foundation
// Licensed under the MIT License

//! The "frontend" program for the WWT Aligner tool. This is just a thin shim
//! that invokes the backend "agent" inside a Docker container, mapping things
//! like filesystem paths.

use std::{ffi::OsString, path::PathBuf};
use structopt::StructOpt;

mod docker;
mod errors;

use errors::Result;

#[derive(Debug, PartialEq, StructOpt)]
#[structopt(about = "align images on the sky")]
struct AlignerFrontendOptions {
    #[structopt(subcommand)]
    command: Commands,
}

trait Command {
    fn execute(self) -> Result<i32>;
}

#[allow(clippy::enum_variant_names)]
#[derive(Debug, PartialEq, StructOpt)]
enum Commands {
    #[structopt(name = "preview")]
    /// Preview a WWT WTML file in the web client.
    Preview(PreviewCommand),

    #[structopt(name = "update")]
    /// Download the latest version of the alignment software.
    Update(UpdateCommand),

    #[structopt(external_subcommand)]
    Other(Vec<OsString>),
}

impl Command for Commands {
    fn execute(self) -> Result<i32> {
        match self {
            Commands::Preview(o) => o.execute(),
            Commands::Update(o) => o.execute(),
            Commands::Other(args) => do_other(args),
        }
    }
}

fn main() {
    let opts = AlignerFrontendOptions::from_args();
    std::process::exit(errors::report(opts.command.execute()));
}

// other

/// Launch an "other" command, which we delegate to the agent running inside the
/// container. We use the "args protocol" to have the agent tell us how to set
/// up the Docker arguments so that it will be able to do the I/O it needs to
/// do.
fn do_other(all_args: Vec<OsString>) -> Result<i32> {
    let db = atry!(
        docker::DockerBuilder::for_analyzed_command(&all_args);
        ["failed to validate command-line arguments"]
    );

    let db = match db {
        docker::AnalysisOutcome::Continue(c) => c,
        docker::AnalysisOutcome::EarlyExit(c) => return Ok(c),
    };

    let mut cmd = db.into_command();
    let status = atry!(
        cmd.status();
        ["failed to launch the Docker command: {:?}", cmd]
    );

    let c = match status.code() {
        Some(0) => 0,
        Some(c) => {
            eprintln!("error: the Docker command signaled failure");
            c
        }
        None => {
            eprintln!("error: the Docker command exited unexpectedly");
            1
        }
    };

    Ok(c)
}

// preview

#[derive(Debug, PartialEq, StructOpt)]
struct PreviewCommand {
    #[structopt(
        long = "port",
        help = "The port number on which to serve the data",
        default_value = "17001"
    )]
    port: u16,

    #[structopt(help = "Preview a WWT WTML file in the web client")]
    wtml_path: PathBuf,
}

impl Command for PreviewCommand {
    fn execute(self) -> Result<i32> {
        let wtml_name = a_ok_or!(
            self.wtml_path.file_name();
            ["the argument should be a WTML filename"]
        );

        let wtml_name = a_ok_or!(
            wtml_name.to_str();
            ["the WTML path argument must be Unicode-compatible"]
        );

        let wtml_name = wtml_name.replace("_rel.wtml", ".wtml");

        let wtml_url = format!(
            "http://localhost:{}/{}",
            self.port,
            percent_encoding::utf8_percent_encode(&wtml_name, percent_encoding::NON_ALPHANUMERIC)
        );

        let wwt_url = format!(
            "https://worldwidetelescope.org/webclient/?wtml={}",
            percent_encoding::utf8_percent_encode(&wtml_url, percent_encoding::CONTROLS)
        );

        // We can't use `do_other()` here since we shouldn't wait for the
        // command to finish running -- it only exits on SIGINT.

        let serve_wtml_args = vec![
            "serve-wtml".into(),
            format!("--port={}", self.port).into(),
            self.wtml_path.clone().into_os_string(),
        ];

        let db = atry!(
            docker::DockerBuilder::for_analyzed_command(&serve_wtml_args);
            ["failed to validate command-line arguments"]
        );

        let db = match db {
            docker::AnalysisOutcome::Continue(c) => c,
            docker::AnalysisOutcome::EarlyExit(c) => return Ok(c),
        };

        let mut cmd = db.into_command();
        let mut child = atry!(
            cmd.spawn();
            ["failed to launch the Docker command: {:?}", cmd]
        );

        // There's a minor race here since we don't know when the child HTTP
        // service will have fully started up. That should be fast, though, and
        // opening a browser window will take time itself.

        println!("Launching {} in your browser ...", wwt_url);

        atry!(
            webbrowser::open(&wwt_url);
            ["failed to launch the web browser"]
        );

        println!("Type control-C to stop the program when finished.");

        let _status = atry!(
            child.wait();
            ["failed to OS-wait on the server command"]
        );

        Ok(0)
    }
}

// update

#[derive(Debug, PartialEq, StructOpt)]
struct UpdateCommand {
    #[structopt(
        long = "latest",
        help = "Update to the \"bleeding edge\" software version"
    )]
    latest: bool,
}

impl Command for UpdateCommand {
    fn execute(self) -> Result<i32> {
        let tag = if self.latest { "latest" } else { "stable" };

        println!("Updating the Docker image to tag \"{}\" ...", tag);
        println!();

        for mut cmd in docker::update_commands(tag).drain(..) {
            let status = atry!(
                cmd.status();
                ["failed to launch the Docker command: {:?}", cmd]
            );

            match status.code() {
                Some(0) => {}
                Some(c) => {
                    eprintln!("error: the Docker command signaled failure");
                    return Ok(c);
                }
                None => {
                    eprintln!("error: the Docker command exited unexpectedly");
                    return Ok(1);
                }
            };

            println!();
        }

        println!("Done!");
        Ok(0)
    }
}
