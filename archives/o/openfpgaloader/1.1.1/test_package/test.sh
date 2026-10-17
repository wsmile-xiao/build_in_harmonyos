#!/usr/bin/env bash
set -euo pipefail

binary="$1"

"$binary" -V 2>&1 | grep -qi "openFPGALoader"
"$binary" --help 2>&1 | grep -qiE "Usage:|program to flash FPGA"

set +e
detect_output=$("$binary" --detect 2>&1)
detect_status=$?
set -e

if [[ $detect_status -eq 0 ]]; then
    grep -qiE "JTAG|FPGA|device|cable" <<<"$detect_output"
else
    # The official runner has no programmer attached. Reaching hardware
    # discovery and reporting that condition still exercises --detect.
    grep -qiE "No (cable|device|USB devices)|not found|unable to open|failed to open" \
        <<<"$detect_output"
fi
