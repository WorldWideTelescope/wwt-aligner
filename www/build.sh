#! /bin/bash
# Copyright 2021 the .NET Foundation
# Licensed under the MIT License.

# A very simple script to build static HTML content for GitHub pages to create a
# redirect to the latest frontend release.

set -euo pipefail

cd "$(dirname $0)"
rm -rf dist
mkdir -p dist/latest-release/

touch dist/.nojekyll

version="$(cranko show version wwt-aligner-frontend)"
url="https://github.com/WorldWideTelescope/wwt-aligner/releases/tag/wwt-aligner-frontend%40$version"
sed -e "s|@target@|${url}|g" index.tmpl.html >dist/latest-release/index.html
