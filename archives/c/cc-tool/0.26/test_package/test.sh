#!/bin/sh
set -eu
tool=${1:?missing packaged cc-tool path}
test -x "$tool"
"$tool" --help 2>&1 | grep -Eq 'Version:[[:space:]]*0\.26'
