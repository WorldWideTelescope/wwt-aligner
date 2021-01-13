# Copyright 2020 the .NET Foundation
# Licensed under the MIT License.

"""Entrypoint for the "wwt-aligner" command-line interface.

"""
import argparse
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


# "go" subcommand

def go_getparser(parser):
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


def go_impl(settings):
    from .driver import go

    work_dir = tempfile.mkdtemp()
    go(
        fits_path = settings.fits_path,
        rgb_path = settings.rgb_path,
        work_dir = work_dir,
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

    impl = globals().get(py_name + '_impl')
    if impl is None:
        die('no such subcommand "{}"'.format(settings.subcommand))

    # OK to go!

    impl(settings)
