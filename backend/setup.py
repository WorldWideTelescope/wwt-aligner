#! /usr/bin/env python
# -*- mode: python; coding: utf-8 -*-
# Copyright 2020 the .NET Foundation
# Distributed under MIT License

import io
from setuptools import setup

with io.open('README.md', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup_args = dict(
    name = 'wwt_aligner',  # cranko project-name
    version = '0.dev0',  # cranko project-version
    description = 'Align RGB images to FITS images using Astrometry.net',
    long_description = LONG_DESCRIPTION,
    long_description_content_type = 'text/markdown',
    url = 'https://github.com/WorldWideTelescope/wwt-aligner',
    license = 'MIT',
    platforms = 'Linux, Mac OS X, Windows',

    author = 'AAS WorldWide Telescope Team',
    author_email = 'wwt@aas.org',

    classifiers = [
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages = [
        'wwt_aligner',
        'wwt_aligner.tests',
    ],

    entry_points = {
        'console_scripts': [
            'wwt-aligner-agent=wwt_aligner.agent_cli:entrypoint',
        ]
    },

    install_requires = [
        'astropy>=4',
        'pyavm>=0.9',
        'sep>=1.1',
        'toasty>=0.4',
    ],

    extras_require = {
        'test': [
            'pytest',
            'pytest-cov>=2.6.1',
        ],
        'docs': [
            'astropy-sphinx-theme',
            'numpydoc',
            'sphinx>=1.6',
            'sphinx-automodapi',
        ],
    },
)

if __name__ == '__main__':
    setup(**setup_args)
