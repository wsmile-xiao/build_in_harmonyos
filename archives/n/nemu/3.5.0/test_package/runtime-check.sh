#!/usr/bin/env bash
# R40 runtime acceptance for the OHOS build of nemu 3.5.0.
#
# Runs the *unmodified* upstream integration suite (test/vm_test.py +
# test/ova_test.py) against the packaged binary. Every prerequisite is probed in
# a single pass so one run reports every blocker; a missing prerequisite is
# never reported as PASS (exit 77 = skip).
#
# usage: runtime-check.sh [/path/to/nemu]
# env:   QEMU_BIN_DIR  NEMU_TEST_DIR  NEMU_TARGET_OS=OHOS
#        NEMU, NEMU_TEST_DIR and the qemu/tmux paths are auto-discovered.
set -uo pipefail

nemu="${1:-${NEMU:-}}"
test_dir="${NEMU_TEST_DIR:-}"
missing=()

# --- discovery -------------------------------------------------------------
if [ -z "$nemu" ]; then
    if command -v nemu >/dev/null 2>&1; then
        nemu="$(command -v nemu)"
    else
        nemu="$(ls -dt /storage/Users/currentUser/.conan2/p/b/nemu*/p/bin/nemu 2>/dev/null | head -1)"
    fi
fi
if [ -z "$test_dir" ]; then
    for c in /storage/Users/currentUser/builds/nemu-3.5.0.work/test \
             /storage/Users/currentUser/builds/nemu-3.5.0.orig/test; do
        if [ -f "$c/vm_test.py" ] && [ -f "$c/ova_test.py" ]; then test_dir="$c"; break; fi
    done
fi

probe() { # <label> <ok?0/1> <detail>
    if [ "$2" -eq 0 ]; then
        printf '  [ok]   %-20s %s\n' "$1" "$3"
    else
        printf '  [MISS] %-20s %s\n' "$1" "$3"
        missing+=("$1")
    fi
}

echo '== nemu 3.5.0 OHOS runtime acceptance =='
echo '-- execution target --'
if [ -n "$nemu" ] && [ -x "$nemu" ]; then
    # A file can carry +x and still fail to load; the loader message is the real
    # technical reason and is what rule4 asks us to record.
    if loader_err="$("$nemu" --version 2>&1 >/dev/null)"; then
        probe 'nemu' 0 "$nemu"
    else
        probe 'nemu' 1 "$nemu -> $(printf '%s' "$loader_err" | head -1)"
    fi
else
    probe 'nemu' 1 "not executable: ${nemu:-<not found>}"
fi

echo '-- upstream suite prerequisites --'
qemu="$(command -v qemu-system-x86_64 2>/dev/null || true)"
if [ -z "$qemu" ] && [ -n "${QEMU_BIN_DIR:-}" ] && [ -x "${QEMU_BIN_DIR}/qemu-system-x86_64" ]; then
    qemu="${QEMU_BIN_DIR}/qemu-system-x86_64"
fi
# Presence is not enough: a +x binary can still fail to load (rc=126). Probe by
# actually executing, so the report carries the real technical reason.
if [ -n "$qemu" ] && err="$("$qemu" -M help 2>&1 >/dev/null)"; then
    probe 'qemu-system-x86_64' 0 "$qemu"
elif [ -n "$qemu" ]; then
    probe 'qemu-system-x86_64' 1 "$qemu -> $(printf '%s' "$err" | head -1)"
else
    probe 'qemu-system-x86_64' 1 'required by test/utils.py:51 (qemu_mtype)'
fi

tmux_bin="$(command -v tmux 2>/dev/null || true)"
if [ -n "$tmux_bin" ] && err="$("$tmux_bin" -V 2>&1 >/dev/null)"; then
    probe 'tmux' 0 "$tmux_bin"
elif [ -n "$tmux_bin" ]; then
    probe 'tmux' 1 "$tmux_bin -> $(printf '%s' "$err" | head -1)"
else
    probe 'tmux' 1 'required to drive the nemu TUI'
fi

if [ -n "$test_dir" ] && [ -f "$test_dir/vm_test.py" ] && [ -f "$test_dir/ova_test.py" ]; then
    probe 'NEMU_TEST_DIR' 0 "$test_dir"
else
    probe 'NEMU_TEST_DIR' 1 'set it to the upstream test/ directory'
fi

if [ -n "$test_dir" ] && [ -f "$test_dir/testdata/dsl.ova" ]; then
    probe 'testdata/dsl.ova' 0 "$test_dir/testdata/dsl.ova"
else
    probe 'testdata/dsl.ova' 1 'ova_test.py:21; fetch with test/run.sh (gdown)'
fi

probe_file="/tmp/nemu-runtime-check.$$"
if : >"$probe_file" 2>/dev/null; then
    probe '/tmp writable' 0 "$probe_file"
    rm -f "$probe_file"
else
    probe '/tmp writable' 1 'test/utils.py:13 mkdir /tmp/nemu_<uuid>'
fi

if [ "${NEMU_TARGET_OS:-}" != 'OHOS' ]; then
    printf '  [warn] %-20s %s\n' 'NEMU_TARGET_OS' 'not OHOS; set it to assert the OHOS runtime'
fi

if [ "${#missing[@]}" -gt 0 ]; then
    printf '\nSKIP: %d prerequisite(s) unavailable: %s\n' \
        "${#missing[@]}" "${missing[*]}" >&2
    exit 77
fi

echo '-- upstream 9 cases --'
export NEMU_BIN_DIR="$(dirname "$nemu")"
export QEMU_BIN_DIR="$(dirname "$qemu")"
log="$(mktemp)"
status=0
(cd "$test_dir" && python3 -m unittest -v vm_test ova_test) 2>&1 | tee "$log" || status=$?
passed="$(grep -cE '\.\.\. ok$' "$log" || true)"
echo "R40_UPSTREAM_N=9 R40_UPSTREAM_PASSED=${passed}"
[ "$status" -eq 0 ] || { echo 'R40_RUNTIME_RESULT=fail' >&2; exit "$status"; }
echo 'R40_RUNTIME_RESULT=pass'
