#!/bin/sh
# Consumer test for the conversion tools shipped by the libabw-tools package.
#
# Usage: test_libabw_cli.sh <path-to-package-bin-dir>
#
# Upstream ships no AbiWord sample, so the tools are driven on inputs whose
# handling is well defined: --version/--info must report cleanly, a missing
# file and a plain-text file must both be rejected with a non-zero status,
# and neither may die from a signal.  That proves the tools link and
# resolve their dependencies (librevenge generators + libxml2).
set -u

BINDIR=${1:-.}
if [ ! -x "$BINDIR/abw2text" ] || [ ! -x "$BINDIR/abw2html" ] || [ ! -x "$BINDIR/abw2raw" ]; then
    echo "not ok - installed tools are missing or not executable in $BINDIR"
    exit 1
fi
echo "ok 1 - installed abw2text/abw2html/abw2raw exist and are executable: $BINDIR"

WORK=cli_work
rm -rf "$WORK"
mkdir -p "$WORK"
printf 'this is not an abiword document\n' > "$WORK/plain.txt"

status=0

# ── --version on all three tools (the CI L2 smoke gate runs exactly this) ─
for tool in abw2text abw2html abw2raw; do
    if "$BINDIR/$tool" --version > "$WORK/$tool.version" 2>&1; then
        echo "ok - $tool --version reports: $(head -1 "$WORK/$tool.version")"
    else
        echo "not ok - $tool --version failed"
        status=1
    fi
done

# ── missing input file must fail with a non-zero exit code ────────────────
if "$BINDIR/abw2text" "$WORK/does-not-exist.abw" > "$WORK/missing.out" 2> "$WORK/missing.err"; then
    echo "not ok - a missing input file fails"
    status=1
else
    echo "ok - a missing input file fails with a non-zero exit code"
fi

# ── plain text must be rejected cleanly (no signal death) ─────────────────
"$BINDIR/abw2text" "$WORK/plain.txt" > "$WORK/plain.out" 2> "$WORK/plain.err"
rc=$?
if [ $rc -eq 0 ]; then
    echo "not ok - plain text was accepted as an AbiWord document"
    status=1
elif [ $rc -ge 128 ]; then
    echo "not ok - plain text processing died from a signal (exit $rc)"
    status=1
else
    echo "ok - plain text is rejected cleanly (exit $rc)"
fi

# ── abw2raw on plain text: same clean-failure contract ────────────────────
"$BINDIR/abw2raw" "$WORK/plain.txt" > "$WORK/raw.out" 2> "$WORK/raw.err"
rc=$?
if [ $rc -eq 0 ]; then
    echo "not ok - abw2raw accepted plain text as an AbiWord document"
    status=1
elif [ $rc -ge 128 ]; then
    echo "not ok - abw2raw died from a signal (exit $rc)"
    status=1
else
    echo "ok - abw2raw rejects plain text cleanly (exit $rc)"
fi

if [ $status -eq 0 ]; then
    echo "ok - all tools handled unsupported input without a crash"
else
    echo "not ok - a tool crashed on unsupported input"
fi

rm -rf "$WORK"
exit $status
