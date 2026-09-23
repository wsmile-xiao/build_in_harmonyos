#!/bin/sh
set -eu

bin_dir=$1
pnr="$bin_dir/nextpnr-ice40"

# ---------------------------------------------------------------------------
# 1. the binary starts and reports the version it was built with
#    (this alone already requires the Boost runtime path to resolve)
# ---------------------------------------------------------------------------

version=$("$pnr" --version 2>&1)
expected="nextpnr-ice40 -- Next Generation Place and Route (Version 0.1)"
case "$version" in
  *"$expected"*) ;;
  *) echo "unexpected --version output: $version"; exit 1 ;;
esac

"$pnr" --help 2>&1 | grep -q "General options"

test -x "$pnr"

# ---------------------------------------------------------------------------
# 2. a real place-and-route run against the iCE40 device database
#
#    The chipdb is generated during the build from the icestorm data, so this
#    is what proves the database is present, valid and usable: an empty design
#    still needs the full device database in order to emit a bitstream.
# ---------------------------------------------------------------------------

work="${TMPDIR:-/tmp}/nextpnr-test-$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

cat > "$work/min.json" <<'JSON'
{
  "creator": "ohos-farm-consumer-test",
  "modules": {
    "top": {
      "attributes": { "top": "0000000000000001" },
      "ports": {},
      "cells": {},
      "netnames": {}
    }
  }
}
JSON

run_pnr() {
    device=$1
    package=$2
    asc="$work/$device.asc"
    log="$work/$device.log"
    "$pnr" "--$device" --package "$package" \
           --json "$work/min.json" --asc "$asc" > "$log" 2>&1
    test -s "$asc"
    grep -q "^\.device " "$asc"
    grep -q "Program finished normally" "$log"
}

run_pnr hx1k tq144
run_pnr hx8k ct256

echo "nextpnr: version, help, and iCE40 place-and-route on hx1k + hx8k producing bitstreams OK"
