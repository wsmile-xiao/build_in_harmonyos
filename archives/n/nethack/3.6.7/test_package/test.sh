#!/bin/sh
# Verify the packaged NetHack binary prints its version and exits cleanly.
set -e
"$1" --version | grep -E "NetHack 3\.6\.7|NetHack, Copyright"