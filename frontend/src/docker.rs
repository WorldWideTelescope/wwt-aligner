// Copyright 2020 the .NET Foundation
// Licensed under the MIT License

//! Tools for driving Docker.

use std::{collections::HashMap, ffi::{OsStr, OsString}, path::{Path, PathBuf}, process::Command};

use crate::{a_ok_or, atry, errors::Result};

const DEFAULT_IMAGE_NAME: &str = "aligner:latest";  // XXX

/// Helper for constructing Docker command lines.
#[derive(Debug)]
pub struct DockerBuilder {
    image_name: String,

    /// Host dirname to in-Docker dirname.
    host_dirs: HashMap<PathBuf, PathBuf>,

    inner_args: Vec<OsString>,
}

impl Default for DockerBuilder {
    fn default() -> Self {
        DockerBuilder {
            image_name: DEFAULT_IMAGE_NAME.to_owned(),
            host_dirs: Default::default(),
            inner_args: Default::default(),
        }
    }
}

impl DockerBuilder {
    pub fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Self {
        self.inner_args.push(arg.as_ref().to_owned());
        self
    }

    pub fn file_arg<P: AsRef<Path>>(&mut self, host_path: P) -> Result<&mut Self> {
        let host_path = host_path.as_ref();
        let host_canon = atry!(
            host_path.canonicalize();
            ["could not determine canonical path for input argument `{}`", host_path.display()]
        );
        let host_dirname = a_ok_or!(
            host_canon.parent();
            ["cannot convey root-type input path `{}` to Docker", host_path.display()]
        );

        let cnt_dirname = self.host_dirs.entry(host_dirname.to_owned()).or_insert_with(|| {
            let mut container_dir = PathBuf::new();
            container_dir.push("/hostdirs");
            let c = host_dirname.display().to_string().replace("/", "_");
            container_dir.push(c);
            container_dir
        });

        // Note that the file name has to come from the canonicalized path, in
        // case it was a symlink to a file with a different actual name.
        let mut cnt_path = cnt_dirname.clone();
        if let Some(n) = host_canon.file_name() {
            cnt_path.push(n);
        }

        self.arg(cnt_path);
        Ok(self)
    }

    pub fn into_command(mut self) -> Command {
        let mut cmd = Command::new("docker");

        cmd.arg("run").arg("--rm");

        for (host_path, cnt_path) in self.host_dirs.drain() {
            cmd.arg("-v");

            let mut vstr = OsString::from(host_path);
            vstr.push(":");
            vstr.push(cnt_path);
            vstr.push(":rw,z");
            cmd.arg(vstr);
        }

        cmd.arg(self.image_name);

        for arg in self.inner_args.drain(..) {
            cmd.arg(arg);
        }

        cmd
    }
}