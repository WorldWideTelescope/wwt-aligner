// Copyright 2020-2021 the .NET Foundation
// Licensed under the MIT License

//! Tools for driving Docker.

use anyhow::ensure;
use serde::Deserialize;
use std::{
    collections::HashMap,
    ffi::{OsStr, OsString},
    io::{self, Write},
    path::PathBuf,
    process::Command,
};

use crate::{a_ok_or, atry, errors::Result};

const DOCKER_COMMAND: &str = "docker";
const DEFAULT_IMAGE_NAME: &str = "aasworldwidetelescope/aligner:latest";
const DEFAULT_INNER_COMMAND: &str = "wwt-aligner-agent";
const SUPPORTED_ARGS_PROTOCOL_VERSION: usize = 1;

/// Helper for constructing Docker command lines.
#[derive(Debug)]
pub struct DockerBuilder {
    image_name: String,
    volumes: Vec<DockerVolume>,
    ports: Vec<DockerPort>,
    inner_args: Vec<OsString>,
}

#[derive(Debug)]
struct DockerVolume {
    host_path: PathBuf,
    container_path: PathBuf,
    read_write: bool,
}

#[derive(Debug)]
struct DockerPort {
    host_ip: String,
    host_port: u16,
    container_port: u16,
}

impl Default for DockerBuilder {
    fn default() -> Self {
        DockerBuilder {
            image_name: DEFAULT_IMAGE_NAME.to_owned(),
            volumes: Default::default(),
            ports: Default::default(),
            inner_args: Default::default(),
        }
    }
}

impl DockerBuilder {
    pub fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Self {
        self.inner_args.push(arg.as_ref().to_owned());
        self
    }

    pub fn for_analyzed_command(args: &[OsString]) -> Result<Option<Self>> {
        let mut analyze_cmd = Command::new(DOCKER_COMMAND);
        analyze_cmd
            .arg("run")
            .arg("--rm")
            .arg(DEFAULT_IMAGE_NAME)
            .arg(DEFAULT_INNER_COMMAND)
            .arg("--x-analyze-args-mode")
            .args(args);

        let output = atry!(
            analyze_cmd.output();
            ["failed to launch the Docker command: {:?}", analyze_cmd]
        );

        // If there was any stderr output, get it out there.
        atry!(
            io::stderr().write_all(&output.stderr);
            ["failed to transfer Docker error output to stderr"]
        );

        if let Some(0) = output.status.code() {
        } else {
            if let Some(c) = output.status.code() {
                if c == 2 {
                    // Signifies a failure to parse arguments according to
                    // Python argparse's defaults. In that case, the usage
                    // message will have already been written to stderr, so
                    // return a value indicating failure that has already
                    // been reported.
                    return Ok(None);
                }

                // Otherwise, something went unexpectedly wrong.

                eprintln!(
                    "error: the Docker command signaled failure (error code {})",
                    c
                );
            } else {
                eprintln!("error: the Docker command exited unexpectedly");
            }

            if !output.stdout.is_empty() {
                eprintln!("error: the command's primary output was:\n");
                atry!(
                    io::stderr().write_all(&output.stdout);
                    ["failed to transfer Docker stdout output"]
                );
            }
        }

        // OK, the command seems to have succeeded. Get the arg info from its
        // output.

        // TODO: recognize `--help` mode

        let mut apdata: ArgsProtocolData = atry!(
            serde_json::from_slice(&output.stdout).map_err(|e| {
                eprintln!("error: failed to parse the following args-analysis output:\n\n");
                let _r = io::stderr().write_all(&output.stdout);
                e
            });
            ["internal error: failed to parse args-analysis output as JSON text"]
        );

        ensure!(
            apdata.version <= SUPPORTED_ARGS_PROTOCOL_VERSION,
            "you must upgrade the launcher in order to use this version of the aligner"
        );

        // Finally, create our actual Docker command from the analyzed arguments.

        let mut builder = DockerBuilder::default();
        let mut volumes = HashMap::new();
        let mut arg = String::new();
        let mut args = Vec::new();

        builder.arg(DEFAULT_INNER_COMMAND);

        for piece in apdata.pieces.drain(..) {
            let is_path = piece.path_pre_exists || piece.path_created;

            let processed_piece = if !is_path {
                piece.text
            } else {
                // A path argument. We've got to prep to mount this path's
                // containing directory as a volume inside the Docker container,
                // with remapping.
                //
                // First, we need to make sure to transform this into a
                // canonical (fully resolved) host path, because if the path
                // contains a symlink the Docker volume mapping can fail in all
                // sorts of ways. But even this step is tricky, because the
                // canonicalization step will fail if the path does not exist,
                // which will be the case for output files.

                let host_path = if piece.path_pre_exists {
                    // This path should exist. We can (must) use std::fs::canonicalize
                    // (in case the final path component is a symlink).
                    atry!(
                        std::fs::canonicalize(&piece.text);
                        ["failed to resolve filesystem path `{}`", &piece.text]
                    )
                } else {
                    // The path will be created. We'll assume that it will be
                    // blown away if it already exists, so we don't bother to
                    // test if it does. But we also assume that its immediate
                    // containing directory exists.

                    let mut path_pieces = piece.text.rsplitn(2, std::path::is_separator);
                    let basename = a_ok_or!(
                        path_pieces.next();
                        ["cannot process empty input path `{}`", &piece.text]
                    );
                    let dirname = path_pieces.next().unwrap_or(".");

                    let mut canon = atry!(
                        std::fs::canonicalize(&dirname);
                        ["failed to resolve directory of output path `{}`", &piece.text]
                    );

                    canon.push(basename);
                    canon
                };

                // OK, now that we have the canonical host path, we can determine its
                // containing directory.

                let mut host_dir = host_path.clone();
                host_dir.pop();

                // Make up a container path for this host path.

                let container_dir = format!(
                    "/volumes/{}",
                    host_dir.to_string_lossy().replace(
                        |c: char| !c.is_alphanumeric() || std::path::is_separator(c),
                        "_"
                    )
                );

                let host_fn = a_ok_or!(
                    host_path.file_name();
                    ["cannot process path `{}`, which lacks a filename component", &piece.text]
                );

                let host_fn = a_ok_or!(
                    host_fn.to_str();
                    ["cannot handle path `{}`, which resolves to something inexpressible as Unicode", &piece.text]
                );

                let container_path = format!("{}/{}", container_dir, host_fn);

                // Add secret hidden arguments enabling the agent to pretend
                // that its internal container paths are host paths.

                builder.arg("--x-host-path");
                builder.arg(piece.text);
                builder.arg("--x-container-path");
                builder.arg(&container_path);

                // Ensure that we will have a Docker volume mount so that this
                // file can be accessed inside the container.

                let vol = volumes.entry(host_dir.clone()).or_insert(DockerVolume {
                    host_path: host_dir,
                    container_path: container_dir.into(),
                    read_write: false,
                });

                if piece.path_created {
                    vol.read_write = true;
                }

                // Finally, the ultimate "processed" value of this argument to propagate
                // into the docker container:
                container_path
            };

            // We can finally actually deal with this as an argument.

            arg.push_str(&processed_piece);

            if !piece.incomplete {
                args.push(arg.clone());
                arg.clear();
            }
        }

        if !arg.is_empty() {
            args.push(arg);
        }

        // We have handled all of the arg pieces! Now that all of the magic
        // `--x-*-path` args are in place, we can add the real args.

        for arg in args.drain(..) {
            builder.arg(arg);
        }

        // Deal with the easier stuff and we're done.

        for (_, vi) in volumes.drain() {
            builder.volumes.push(vi);
        }

        for port in apdata.published_ports.drain(..) {
            builder.ports.push(port.into());
        }

        Ok(Some(builder))
    }

    pub fn into_command(mut self) -> Command {
        let mut cmd = Command::new(DOCKER_COMMAND);

        cmd.arg("run").arg("--rm").arg("-it");

        for vol in self.volumes.drain(..) {
            cmd.arg("-v");

            let mut vstr = OsString::from(vol.host_path);
            vstr.push(":");
            vstr.push(vol.container_path);
            vstr.push(":");
            vstr.push(if vol.read_write { "rw" } else { "ro" });
            cmd.arg(vstr);
        }

        for port in self.ports.drain(..) {
            cmd.arg("-p");
            cmd.arg(format!(
                "{}:{}:{}",
                port.host_ip, port.host_port, port.container_port
            ));
        }

        let uid = nix::unistd::geteuid();
        cmd.arg("-e").arg(format!("HOST_UID={}", uid));

        let gid = nix::unistd::getegid();
        cmd.arg("-e").arg(format!("HOST_GID={}", gid));

        cmd.arg(self.image_name);

        for arg in self.inner_args.drain(..) {
            cmd.arg(arg);
        }

        cmd
    }
}

/// Generate a Command that will update the Docker image.
pub fn update_command() -> Command {
    let mut cmd = Command::new(DOCKER_COMMAND);
    cmd.arg("pull").arg(DEFAULT_IMAGE_NAME);
    cmd
}

/// The main "args protocol" data payload.
#[derive(Debug, Deserialize)]
struct ArgsProtocolData {
    version: usize,
    pieces: Vec<ArgsProtocolPieceInfo>,

    #[serde(default)]
    published_ports: Vec<ArgsProtocolPortInfo>,
}

/// Information about a portion of a command-line argument.
///
/// Arguments are broken into pieces so that portions corresponding to
/// filesystem paths can be identified. The frontend needs to understand how
/// paths are used by the backend so that it can set up the appropriate mounts
/// inside the Docker environment.
#[derive(Debug, Deserialize)]
struct ArgsProtocolPieceInfo {
    /// The argument text.
    text: String,

    /// If true, there should be a subsequent argument piece that will be
    /// concatenated to this one without being broken into a separate argument,
    /// and without any whitespace being added.
    #[serde(default)]
    incomplete: bool,

    /// If true, this piece corresponds to a filesystem path on the host, that
    /// should exist before the tool runs.
    #[serde(default)]
    path_pre_exists: bool,

    /// If true, this piece corresponds to a filesystem path on the host, and it
    /// will be created by the tool. Therefore the containing directory of this
    /// path should be mounted read-write inside the container.
    #[serde(default)]
    path_created: bool,
}

#[derive(Debug, Deserialize)]
struct ArgsProtocolPortInfo {
    #[serde(default = "default_port_ip")]
    host_ip: String,

    host_port: u16,

    container_port: u16,
}

fn default_port_ip() -> String {
    "127.0.0.1".to_owned()
}

impl From<ArgsProtocolPortInfo> for DockerPort {
    fn from(ap: ArgsProtocolPortInfo) -> DockerPort {
        DockerPort {
            host_ip: ap.host_ip,
            host_port: ap.host_port,
            container_port: ap.container_port,
        }
    }
}
