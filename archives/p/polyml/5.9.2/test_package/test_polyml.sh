#!/usr/bin/env sh
set -eu
poly=${1:?installed poly executable is required}
script=${2:?Standard ML test script is required}
"$poly" --script "$script"
