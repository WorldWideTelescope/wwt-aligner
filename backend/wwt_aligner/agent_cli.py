# Copyright 2020 the .NET Foundation
# Licensed under the MIT License.

"""
Entrypoint for the "wwt-aligner[-agent]" command-line interface.

"""
import argparse
import json
import os.path
import shutil
import sys
import tempfile

__all__ = ['entrypoint']


# General CLI utilities

def die(msg):
    print('error:', msg, file=sys.stderr)
    sys.exit(1)

def warn(msg):
    print('warning:', msg, file=sys.stderr)


# The agent is generally expected to run inside a Docker container. In order to
# be able to do its input and output, then, its container needs to be set up
# with the appropriate filesystem mounts by the program that launches it. So
# there needs to be some kind of analysis of the program arguments and
# identification of which directories need to be mounted on the launcher side.
#
# But as long as we're running the agent inside Docker, it is/would be *really*
# nice to be able to get new CLI commands just by updating the container. We
# could ask people to update the launcher but would prefer if it didn't have to
# stay in close sync with the containerized app. You could imagine a self-update
# scheme where we update the launcher with a binary stored inside the container,
# but that's a bit tricky to implement.
#
# Instead, we the launcher run each command twice, the first time passing in a
# special hidden `--x-analyze-args-mode` flag. When this flag is active, the agent
# returns JSON specifying what kind of environment setup the launcher needs to
# perform. The agent then runs the command "for real" as instructed. This way
# the launcher can start handling new commands without needing to explicitly
# know about them. This handshake is the "args protocol".

ARGS_PROTOCOL_VERSION = 1

class ArgPiece(object):
    text = None
    "The text of this argument piece."

    incomplete = False
    """If true, the subsequent arg piece should be concatenated to this one
    without a space. This allows us to handle arguments of the form
    `--path=./somepath.txt`."""

    path_pre_exists = False
    """If true, this piece is a filesystem path and it should exist before the
    program starts running."""

    path_created = False
    """If true, this piece is a filesystem path that the program will create
    during its exection. Therefore its containing directory should be mounted
    read-write in the Docker container."""

    def __init__(self, text, incomplete=False, path_pre_exists=False, path_created=False):
        self.text = str(text)
        self.incomplete = incomplete
        self.path_pre_exists = path_pre_exists
        self.path_created = path_created

    def as_json(self):
        data = {'text': self.text}

        if self.incomplete:
            data['incomplete'] = True

        if self.path_pre_exists:
            data['path_pre_exists'] = True

        if self.path_created:
            data['path_created'] = True

        return data


class PublishedPort(object):
    host_ip = None
    """The IP address specification for the interface on the host that should listen
    for connections. If unspecified, defaults to the local loopback interface."""

    host_port = None
    "The port number on the host side."

    container_port = None
    "The port number on the container side."

    def __init__(self, host_port, container_port, host_ip=None):
        self.host_ip = host_ip
        self.host_port = host_port
        self.container_port = container_port

    def as_json(self):
        data = {
            'host_port': self.host_port,
            'container_port': self.container_port,
        }

        if self.host_ip is not None:
            data['host_ip'] = self.host_ip

        return data


class ArgsProtocolBuilder(object):
    pieces = None
    ports = None

    def __init__(self):
        self.pieces = []
        self.ports = []

    def add_arg(self, arg, incomplete=False):
        """
        Add an argument that needs no translation from the host to the container.
        """
        self.pieces.append(ArgPiece(arg, incomplete=incomplete))
        return self

    def add_path_arg(self, path, incomplete=False, pre_exists=False, created=False):
        """
        Add an argument that is a path on the host.
        """
        assert pre_exists or created
        self.pieces.append(ArgPiece(
            path,
            incomplete = incomplete,
            path_pre_exists = pre_exists,
            path_created = created,
        ))
        return self

    def add_published_port(self, host_port, container_port, host_ip=None):
        self.ports.append(PublishedPort(host_port, container_port, host_ip=host_ip))
        return self

    def write_as_json(self, fp):
        data = {
            'version': ARGS_PROTOCOL_VERSION,
            'pieces': [p.as_json() for p in self.pieces],
            'published_ports': [p.as_json() for p in self.ports],
        }
        json.dump(data, fp, ensure_ascii=False, indent=2, sort_keys=True)


# "go" subcommand

def go_getparser(parser):
    parser.add_argument(
        '--anet-bin-prefix',
        default = '',
        help = 'A prefix to apply to the names of Astrometry.Net programs to run',
    )
    parser.add_argument(
        '--output', '-o',
        dest = 'output_path',
        required = True,
        help = 'The path of the new AVM-tagged image to output',
    )
    parser.add_argument(
        '--tile', '-t',
        dest = 'tile_path',
        help = 'The path to output the image in AAS WorldWide Telescope tiled format',
    )
    parser.add_argument(
        'fits_path',
        metavar = 'FITS-PATH',
        help = 'The path to input FITS file',
    )
    parser.add_argument(
        'rgb_path',
        metavar = 'RGB-PATH',
        help = 'The path to input file to solve',
    )


def go_analyze_args(builder, settings):
    if settings.anet_bin_prefix:
        builder.add_arg(f'--anet-bin-prefix={settings.anet_bin_prefix}')

    builder.add_arg('--output=', incomplete=True)
    builder.add_path_arg(settings.output_path, created=True)

    if settings.tile_path:
        builder.add_arg('--tile=', incomplete=True)
        builder.add_path_arg(settings.tile_path, created=True)

    builder.add_path_arg(settings.fits_path, pre_exists=True)
    builder.add_path_arg(settings.rgb_path, pre_exists=True)


def go_impl(settings):
    from .driver import go

    work_dir = tempfile.mkdtemp()
    go(
        fits_path = settings.fits_path,
        rgb_path = settings.rgb_path,
        output_path = settings.output_path,
        tile_path = settings.tile_path,
        work_dir = work_dir,
        anet_bin_prefix = settings.anet_bin_prefix,
    )
    shutil.rmtree(work_dir)


# The CLI driver:

def entrypoint(args=None):
    """The entrypoint for the \"wwt-aligner\" command-line interface.

    Parameters
    ----------
    args : iterable of str, or None (the default)
      The arguments on the command line. The first argument should be
      a subcommand name or global option; there is no ``argv[0]``
      parameter.

    """
    # Set up the subcommands from globals()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--x-analyze-args-mode',
        dest = 'analyze_args_mode',
        action = 'store_true',
        help = argparse.SUPPRESS,
    )
    parser.add_argument(
        '--x-host-path',
        dest = 'host_paths',
        action = 'append',
        help = argparse.SUPPRESS,
    )
    parser.add_argument(
        '--x-container-path',
        dest = 'container_paths',
        action = 'append',
        help = argparse.SUPPRESS,
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    commands = set()

    for py_name, value in globals().items():
        if py_name.endswith('_getparser'):
            cmd_name = py_name[:-10].replace('_', '-')
            subparser = subparsers.add_parser(cmd_name)
            value(subparser)
            commands.add(cmd_name)

    # What did we get?

    settings = parser.parse_args(args)

    if settings.subcommand is None:
        print('Run me with --help for help. Allowed subcommands are:')
        print()
        for cmd in sorted(commands):
            print('   ', cmd)
        return

    py_name = settings.subcommand.replace('-', '_')

    if not settings.analyze_args_mode:
        # Just Do It.
        impl = globals().get(py_name + '_impl')
        if impl is None:
            die('no such subcommand "{}"'.format(settings.subcommand))

        impl(settings)
    else:
        # We're in args-analysis mode.
        aa = globals().get(py_name + '_analyze_args')
        if aa is None:
            die('no such (analyzable) subcommand "{}"'.format(settings.subcommand))

        builder = ArgsProtocolBuilder()
        builder.add_arg(settings.subcommand)
        aa(builder, settings)
        builder.write_as_json(sys.stdout)
        print()
