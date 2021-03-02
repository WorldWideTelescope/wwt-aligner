#! /bin/bash
# Copyright 2021 the .NET Foundation
# Licensed under the MIT License.
#
# This is the "entrypoint" script for the backend docker container. When the
# frontend runs "docker run frontend foo bar", we are invoked with $1=foo and
# $2=bar. This script is responsible for executing the main program under the
# UID and GID of the invoking process on the host. These must be propagated to
# the container in the environment variables HOST_UID and HOST_GID.

uid="${HOST_UID:-0}"
gid="${HOST_GID:-0}"

# Get the name of a group with the GID. If one doesn't already exist, create
# one. (We take this approach so that the entrypoint can run successfully
# multiple times within the same container, if needed. Also, note that the
# system may come preloaded with a group with the given GID.)
gname=$(grep "^[^:]*:[^:]*:$gid:" /etc/group |cut -d: -f1)
if [ -z "$gname" ] ; then
    gname="grp$gid"
    addgroup --quiet --gid "$gid" "$gname"
fi

# Same deal, for a user with the given UID and primary group GID.
uname=$(grep "^[^:]*:[^:]*:$uid:$gid:" /etc/passwd |cut -d: -f1)
if [ -z "$uname" ] ; then
    uname="u${uid}g${gid}"
    adduser --quiet --uid "$uid" --gid "$gid" --home "/home/$uname" \
      --disabled-password --gecos "$uname" "$uname"
fi

# Ready to rock. We use `sudo` because the inner-shell quoting semantics of `su`
# are a pain.
exec sudo -u "$uname" "$@"