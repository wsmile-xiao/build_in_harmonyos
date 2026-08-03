#!/usr/bin/env bash
set -eu

sisc_bin=${1:?sisc wrapper path required}
bash_bin=${2:-bash}

if ! command -v java >/dev/null 2>&1; then
    echo "[skip] java not found in PATH; sisc-scheme requires an external JVM runtime"
    exit 0
fi

# Exercise the installed wrapper's own relocation logic. Conan runenv may set
# SISC_HOME to a host-native path during local cross prechecks.
unset SISC_HOME

echo "[test] sisc --version"
set +e
version_out=$("$bash_bin" "$sisc_bin" --version 2>&1)
version_rc=$?
set -e
printf '%s\n' "$version_out"
if [ "$version_rc" -ne 0 ]; then
    echo "ERROR: sisc --version exited with $version_rc"
    exit 1
fi
case "$version_out" in
    *"1.16.6"*) ;;
    *)
        echo "ERROR: expected version output to contain 1.16.6"
        exit 1
        ;;
esac

echo "[test] sisc expression evaluation"
set +e
expr_out=$("$bash_bin" "$sisc_bin" -e "(+ 1 2)" -x 2>&1)
expr_rc=$?
set -e
expr_out=${expr_out//$'\r'/}
printf '%s\n' "$expr_out"
if [ "$expr_rc" -ne 0 ]; then
    echo "ERROR: sisc expression command exited with $expr_rc"
    exit 1
fi
if [ "$expr_out" != "3" ]; then
    echo "ERROR: expected Scheme expression output to be 3"
    exit 1
fi

echo "sisc-scheme smoke tests passed"
