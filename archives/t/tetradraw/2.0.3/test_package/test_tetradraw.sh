#!/bin/sh
# tetradraw 2.0.3 — real-execution test for the packaged binaries.
#
# Proves the shipped artifacts are genuine, runnable OHOS aarch64
# executables: it checks the ELF magic, the e_machine field, and then
# actually launches each binary and requires it to reach the program's
# own setup_ncurses() code (which prints its own banner before touching
# the terminal).  A missing / stub / non-OHOS binary fails here.
#
# TERM is set to a name that has no terminfo entry anywhere, so
# initscr() always fails fast and deterministically instead of dropping
# the process into the interactive editor loop.  No LD_PRELOAD / host
# specific path is used: patch 0005 restores a classic POSIX FD_SET in
# src/network.c, so the binaries reference no libc symbol beyond the
# standard OHOS libc / select() ABI.
set -u
BIN_DIR="${1:?usage: test_tetradraw.sh <bin_dir>}"
FAKE_TERM="tetradraw-ci-no-terminfo"

pass=0
total=8

fail() {
    echo "ASSERT FAIL: $1"
    echo "ASSERTIONS $pass/$total passed"
    exit 1
}

# run <binary> -> stdout+stderr of a real execution, exit status in $rc
# `timeout` is only a hang guard; it must exist on any Linux CI image.
run() {
    if command -v timeout >/dev/null 2>&1; then
        out=$(TERM="$FAKE_TERM" timeout 30 "$1" </dev/null 2>&1)
    else
        out=$(TERM="$FAKE_TERM" "$1" </dev/null 2>&1)
    fi
    rc=$?
}

# ── 1/2: both binaries exist and carry the ELF magic ───────────────
for name in tetradraw tetraview; do
    bin="$BIN_DIR/$name"
    [ -f "$bin" ] || fail "$name missing"
    magic=$(od -An -tx1 -N4 "$bin" | tr -d ' \n')
    [ "$magic" = "7f454c46" ] || fail "$name not ELF (magic=$magic)"
    pass=$((pass + 1))
done

# ── 3/4: e_machine == EM_AARCH64 (0xb7, little endian at byte 18) ─
for name in tetradraw tetraview; do
    mach=$(od -An -tx1 -j18 -N2 "$BIN_DIR/$name" | tr -d ' \n')
    [ "$mach" = "b700" ] || fail "$name is not aarch64 (e_machine=$mach)"
    pass=$((pass + 1))
done

# ── 5/6: real execution reaches the program's own setup_ncurses() ──
#   The banner in src/term.c is printed unconditionally for any
#   TERM != "linux", i.e. it can only appear if the process actually
#   started, ran main() and entered the TUI setup path.
for name in tetradraw tetraview; do
    run "$BIN_DIR/$name"
    case "$out" in
        *"have only been tested under the linux-console"*) : ;;
        *"Error relocating"*|*"symbol not found"*|*"cannot open shared object"*)
            fail "$name did not load: $out" ;;
        *) fail "$name never reached setup_ncurses(): rc=$rc out=$out" ;;
    esac
    pass=$((pass + 1))
done

# ── 7/8: the run ended in a normal exit, not a loader, hang or signal
#   death.  124 = timeout guard fired (fell into the editor loop),
#   127 = loader/exec failure, >=128 = killed by a signal (e.g. SIGSEGV
#   from an unresolved libc symbol).
for name in tetradraw tetraview; do
    run "$BIN_DIR/$name"
    [ "$rc" -ne 124 ] || fail "$name hung (timeout guard fired)"
    [ "$rc" -ne 127 ] || fail "$name exited 127 (dynamic loader failure)"
    [ "$rc" -lt 128 ] || fail "$name died on signal (exit $rc)"
    pass=$((pass + 1))
done

echo "ASSERTIONS $pass/$total passed"
[ "$pass" -eq "$total" ] || fail "only $pass/$total assertions passed"
echo "TEST_RESULT=pass"
