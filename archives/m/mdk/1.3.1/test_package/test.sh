#!/bin/sh
# test_package/test.sh - smoke test for mdk 1.3.1 executables
# Runs in conanrun env (PATH includes the installed bin/ with mixasm+mixvm).
set -eu

# HMDFS: /tmp may be a read-only mount and the conan build-tree cwd may be
# inaccessible (getcwd fails). Capture the starting dir (it holds the
# vendored hello.mixal next to this script) BEFORE moving to the injected
# writable scratch dir, and never write to /tmp.
ORIG_DIR="$(pwd)"
SCRIPT_DIR="$(dirname "$0")"
SCRATCH="${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}"
mkdir -p "$SCRATCH"
cd "$SCRATCH"

MIXASM_BIN="${MIXASM_BIN:-mixasm}"
MIXVM_BIN="${MIXVM_BIN:-mixvm}"

echo "[test] $MIXASM_BIN --help"
ASM_HELP_OUT="$("$MIXASM_BIN" --help 2>&1)" || {
    echo "FAIL mixasm --help failed (exit $?)"
    exit 1
}
echo "$ASM_HELP_OUT" | grep -qi "usage" || {
    echo "FAIL mixasm --help output missing usage line"
    exit 1
}

echo "[test] $MIXVM_BIN --help"
VM_HELP_OUT="$("$MIXVM_BIN" --help 2>&1)" || {
    echo "FAIL mixvm --help failed (exit $?)"
    exit 1
}
echo "$VM_HELP_OUT" | grep -qi "usage" || {
    echo "FAIL mixvm --help output missing usage line"
    exit 1
}

echo "[test] $MIXASM_BIN assembles hello.mixal"
# hello.mixal is vendored from upstream samples/hello.mixal; it lives next
# to this script (conan test_package keeps the recipe folder as the starting
# cwd). ORIG_DIR/SCRIPT_DIR were captured before cd SCRATCH, so search them
# first; only then fall back to a bounded search under ORIG_DIR.
FIXTURE=""
for candidate in "$ORIG_DIR/hello.mixal" "$SCRIPT_DIR/hello.mixal" "$HOME/hello.mixal"; do
    if [ -f "$candidate" ]; then
        FIXTURE="$candidate"
        break
    fi
done
if [ -z "$FIXTURE" ]; then
    FIXTURE="$(find "$ORIG_DIR" -maxdepth 3 -name hello.mixal 2>/dev/null | head -n 1)"
fi
if [ -z "$FIXTURE" ] || [ ! -f "$FIXTURE" ]; then
    echo "FAIL hello.mixal fixture not found (searched $ORIG_DIR, $SCRIPT_DIR)"
    exit 1
fi
cp "$FIXTURE" "$SCRATCH/hello.mixal"
# Upstream syntax: mixasm [-o OUTPUT_FILE] file (options before the file).
"$MIXASM_BIN" -o "$SCRATCH/hello.mix" "$SCRATCH/hello.mixal" || {
    echo "FAIL mixasm could not assemble hello.mixal (exit $?)"
    exit 1
}
if [ ! -s "$SCRATCH/hello.mix" ]; then
    echo "FAIL mixasm produced an empty hello.mix"
    exit 1
fi
echo "[test] assembled hello.mix size: $(wc -c < "$SCRATCH/hello.mix") bytes"

echo "[test] all mdk executable checks PASSED"
exit 0
