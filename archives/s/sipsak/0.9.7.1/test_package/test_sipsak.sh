#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <package_folder>" >&2
    exit 2
fi

package_folder="$1"
executable="$package_folder/bin/sipsak"

test -x "$executable"
"$executable" --version | grep -q "0.9.7"

echo "sipsak version test passed"
