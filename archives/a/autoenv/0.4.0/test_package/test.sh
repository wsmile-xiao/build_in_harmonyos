#!/usr/bin/env bash
set -euo pipefail

mkdir -p project
printf '%s\n' 'AUTOENV_TEST_VALUE=loaded' 'export AUTOENV_TEST_VALUE' > project/.env

export HOME="$PWD/home"
export XDG_STATE_HOME="$PWD/state"
mkdir -p "$HOME" "$XDG_STATE_HOME"
export AUTOENV_ASSUME_YES=1
export AUTOENV_VIEWER=cat

. "$AUTOENV_ACTIVATE"
cd project

if [ "${AUTOENV_TEST_VALUE:-}" != "loaded" ]; then
    echo "autoenv did not source .env" >&2
    exit 1
fi

printf '%s\n' "autoenv smoke test passed"
