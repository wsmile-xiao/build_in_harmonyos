#!/usr/bin/env sh
set -eu
httping_bin="$1"
"$httping_bin" -V
"$httping_bin" --help
