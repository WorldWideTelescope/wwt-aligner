// Copyright 2020 the .NET Foundation
// Licensed under the MIT License

//! The "frontend" program for the WWT Aligner tool. This is just a thin shim
//! that invokes the backend "agent" inside a Docker container, mapping things
//! like filesystem paths.

use std::path::PathBuf;
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
    #[structopt(name = "go")]
    /// Run the alignment process end-to-end.
    Go(GoCommand),

    #[structopt(name = "help")]
    /// Get help for this tool.
    Help(HelpCommand),
}

impl Command for Commands {
    fn execute(self) -> Result<i32> {
        match self {
            Commands::Go(o) => o.execute(),
            Commands::Help(o) => o.execute(),
        }
    }
}

fn main() {
    let opts = AlignerFrontendOptions::from_args();
    std::process::exit(errors::report(opts.command.execute()));
}

// go

#[derive(Debug, PartialEq, StructOpt)]
struct GoCommand {
    filenames: Vec<PathBuf>,
}

impl Command for GoCommand {
    fn execute(mut self) -> Result<i32> {
        let mut db = docker::DockerBuilder::default();

        db.arg("wwt-aligner-agent");
        db.arg("go");

        for path in self.filenames.drain(..) {
            db.file_arg(path)?;
        }

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
}

// help

#[derive(Debug, PartialEq, StructOpt)]
struct HelpCommand {
    command: Option<String>,
}

impl Command for HelpCommand {
    fn execute(self) -> Result<i32> {
        match self.command.as_deref() {
            None => {
                AlignerFrontendOptions::clap().print_long_help()?;
                println!();
                Ok(0)
            }

            Some(cmd) => {
                AlignerFrontendOptions::from_iter(&[&std::env::args().next().unwrap(), cmd, "--help"])
                    .command
                    .execute()
            }
        }
    }
}