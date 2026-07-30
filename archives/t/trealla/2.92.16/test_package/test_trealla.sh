#!/bin/sh
set -eu

"$1" -q -f -g halt "$2"
