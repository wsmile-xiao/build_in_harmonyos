#!/bin/sh
# jnoisemeter 0.4.1 packaged-tool smoke test.
#
# jnoisemeter is an X11 GUI client of a running JACK server, so it cannot run
# to completion headless on OHOS/CI. The pass condition is therefore that the
# packaged ELF loads its full runtime shared-library closure (clxclient,
# clthreads, libXft, libX11, libjack and their transitive NEEDED entries) and
# reaches a normal upstream exit path instead of dying in the dynamic loader.
#
#   jnoisemeter -h   upstream help() prints the banner "jnoisemeter-0.4.1" to
#                    stderr and calls exit(1). The banner proves the ELF
#                    started, that every NEEDED library resolved, and that
#                    -DVERSION survived the Makefile patch.
#   jnoisemeter      with no DISPLAY available upstream prints
#                    "Can't open display." and returns 1. Returning anything
#                    other than 127 proves the loader closure resolved; 127 is
#                    the "shared library not found" signature.
#
# Usage: test_jnoisemeter.sh <path-to-bin-dir>

# 严格模式（§25 脚本规范）：-e 让任何未显式 guard 的失败立即中断，不给"跑到底打印 PASS"的
# 假通过留路；-o pipefail 让管道里任一段失败都被看见。代价是本脚本两处**故意**失败的上游
# 行为必须显式 guard（见下方 `|| true` / `|| rc=$?`），否则会被严格模式误判成测试失败。
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "usage: $0 <path-to-bin-dir>" >&2
    exit 2
fi

BIN_DIR="$1"
BIN="$BIN_DIR/jnoisemeter"

if [ ! -f "$BIN" ]; then
    echo "FAIL: jnoisemeter not found in $BIN_DIR" >&2
    exit 1
fi

# 1) -h must print the version banner. Upstream help() prints it and then calls
#    exit(1) by design, so the *pipeline* status must not be used as the verdict
#    (with pipefail it would always look like a failure): capture the output first,
#    then assert on the text.
banner="$("$BIN" -h 2>&1 || true)"
case "$banner" in
*jnoisemeter-0.4.1*) ;;
*)
    echo "FAIL: jnoisemeter -h did not print the version banner" >&2
    printf "%s
" "$banner" >&2
    exit 1
;;
esac

# 2) A bare run must fail on the missing display, not on the loader. The expected
#    exit code is 1, so capture it instead of letting set -e abort the script.
rc=0
env -u DISPLAY -u XAUTHORITY "$BIN" >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 127 ]; then
    echo "FAIL: jnoisemeter exited 127, runtime shared-library closure unresolved" >&2
    exit 1
fi
if [ "$rc" -ne 1 ]; then
    echo "FAIL: jnoisemeter returned $rc, expected 1 (no display available)" >&2
    exit 1
fi

echo "JNOISEMETER_SMOKE_PASS banner=1 nodisplay_exit=1"
exit 0
