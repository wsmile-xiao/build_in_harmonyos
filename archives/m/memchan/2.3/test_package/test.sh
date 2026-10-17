#!/bin/sh
set -eu

if [ "$#" -lt 3 ]; then
    echo "usage: test.sh [runner ...] tclsh test-script package-libdir" >&2
    exit 2
fi

exec "$@"
