// Copyright 2020-2021 the .NET Foundation
// Licensed under the MIT License

//! The "frontend" program for the WWT Aligner tool. This is just a thin shim
//! that invokes the backend "agent" inside a Docker container, mapping things
//! like filesystem paths.

use std::ffi::OsString;
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
    #[structopt(name = "update")]
    /// Download the latest version of the alignment software.
    Update(UpdateCommand),

    #[structopt(external_subcommand)]
    Other(Vec<OsString>),
}

impl Command for Commands {
    fn execute(self) -> Result<i32> {
        match self {
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

// update

#[derive(Debug, PartialEq, StructOpt)]
struct UpdateCommand {}

impl Command for UpdateCommand {
    fn execute(self) -> Result<i32> {
        println!("Updating the Docker image ...");
        println!();

        let mut cmd = docker::update_command();
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

        println!();
        println!("Done!");
        Ok(c)
    }
}
