#!/data/service/hnp/bin/bash
# test_ohos/run_ohos_test.sh — HarmonyOS PC consumer test runner for pen 0.34.1
#
# Usage:
#   bash run_ohos_test.sh [<prefix>]
#
#   <prefix>  installation prefix that contains bin/ (pen, penlog, penlogd,
#             penctl, mergelogs). When omitted, the binaries already on PATH
#             are used.
#
# The suite itself lives in ../test_package/test.sh so that the exact same
# cases run in `conan create` (test_package) and on a hand-installed prefix —
# there is only one copy of the logic to keep honest.
#
# Cases: see ../test_package/test.sh and ../test_package/MANIFEST.yml
#   OHOS-T1  UDP data plane    penlog -> pen(-U) -> penlogd
#   OHOS-T2  TCP control plane penctl  -> pen control port
#   OHOS-T3  TCP data plane    penctl  -> pen(A) data port -> pen(B) control port
#   OHOS-T4  statistics plane  USR1 + -w -> HTML status page
# `set -u` only (no -e / -o pipefail): this runner execs the suite below, whose
# exit code already aggregates every case's result (see test.sh's own header);
# an early abort here would only obscure where a failure happened.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
SUITE="$HERE/../test_package/test.sh"

if [ ! -f "$SUITE" ]; then
    echo "[FATAL] consumer suite not found: $SUITE"
    exit 2
fi

if [ $# -ge 1 ] && [ -n "$1" ]; then
    echo "[info] using installation prefix: $1"
    export PATH="$1/bin:$PATH"
fi

exec "${BASH:-/data/service/hnp/bin/bash}" "$SUITE"
