#!/bin/sh
# mesa 26.1.5 consumer e2e on DAYU200 (OpenHarmony 6.0.0.47, aarch64).
#
# device_runner.sh uploads only TOP-LEVEL files of the payload directory, so the
# executable and its mesa shared libraries live in the same flat directory and
# the binary carries RUNPATH=$ORIGIN.
HERE=$(cd "$(dirname "$0")" && pwd)
BIN="$HERE/mesa_device_e2e"

echo "=== device: $(uname -m) ==="
# Artifact sanity: refuse to report success on a missing/empty executable.
if [ ! -s "$BIN" ]; then
    echo "FATAL: $BIN missing or empty"
    exit 2
fi
echo "binary size = $(wc -c < "$BIN") bytes"
command -v sha256sum >/dev/null 2>&1 && echo "binary sha256 = $(sha256sum "$BIN" | cut -d' ' -f1)"
command -v md5sum    >/dev/null 2>&1 && echo "binary md5    = $(md5sum "$BIN" | cut -d' ' -f1)"

export LD_LIBRARY_PATH="$HERE"
"$BIN"
rc=$?
echo "consumer_exit=$rc"
exit $rc
