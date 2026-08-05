#!/bin/sh
set -eu

tart="$1"

"$tart" --help | grep "LinuxTaRT" >/dev/null
"$tart" --license | grep "GNU General Public License" >/dev/null
