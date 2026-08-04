#!/bin/sh
set -eu

"$1/nsd" -v
"$1/nsd-checkconf" "$2"
"$1/nsd-checkzone" example.test "$3"
