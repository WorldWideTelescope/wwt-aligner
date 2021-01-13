// Copyright 2020 the .NET Foundation
// Licensed under the MIT License

//! The "frontend" program for the WWT Aligner tool. This is just a thin shim
//! that invokes the backend "agent" inside a Docker container, mapping things
//! like filesystem paths.

use structopt::StructOpt;

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
struct GoCommand {}

impl Command for GoCommand {
    fn execute(self) -> Result<i32> {
        println!("Hello, world!");
        Ok(0)
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