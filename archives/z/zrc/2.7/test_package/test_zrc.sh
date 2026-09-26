#!/bin/sh
# Consumer test for zrc CLI (package bin dir passed as $1):
#   1. --version probe (banner "zrc v2.7" on stderr; upstream exits 1
#      since no script follows — tolerated, banner is the real check)
#   2. -c one-liner with the echo builtin (output check; upstream zrc
#      derives its exit code from the $status variable, which echo does
#      not update, so exit codes of echo-only runs are not asserted)
#   3. -c command substitution + expr arithmetic
#   4. real script file: variables, [inc] arithmetic and do/while
#      control flow (reduced from upstream examples/99bottles.zrc),
#      terminated with an explicit `exit 0` for a deterministic status
set -e

BINDIR="$1"
ZRC="${BINDIR:+$BINDIR/}zrc"

work="${TMPDIR:-.}/zrc_test.$$"
mkdir -p "$work"
cd "$work"

fails=0

check() { # check <desc> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "ok - $1"
    else
        echo "FAIL: $1 (expected [$2], got [$3])"
        fails=$((fails+1))
    fi
}

# 1. --version (banner on stderr; upstream falls through to a bare
#    `return stonum($status)` and exits 1 — same shape as jpnevulator)
rc=0
"$ZRC" --version > /dev/null 2> version.txt || rc=$?
if [ "$rc" -le 1 ]; then
    echo "ok - --version tolerated exit ($rc)"
else
    echo "FAIL: --version exited $rc"
    fails=$((fails+1))
fi
check "--version banner" "zrc v2.7" "$(cat version.txt)"

# 2. -c one-liner: echo builtin (output only, see note above)
check "-c echo builtin" "hello-from-zrc" \
    "$("$ZRC" -c 'echo hello-from-zrc' 2>/dev/null)"

# 3. -c command substitution + expr arithmetic
check "-c expr arithmetic" "42" \
    "$("$ZRC" -c 'echo [expr 13 + 29]' 2>/dev/null)"

# 4. real script (reduced from upstream examples/99bottles.zrc):
#    set / variable expansion / [inc] / do-while / exit status
cat > bottles.zrc <<'EOF'
set bot = 3
do {
	echo $bot bottles of beer on the wall,
	echo [inc bot -1] bottles of beer on the wall!\n
} while {$bot > 1}
echo done
exit 0
EOF
rc=0
"$ZRC" bottles.zrc > bottles.out 2> bottles.err || rc=$?
check "script execution exit code" "0" "$rc"
if grep -q "^3 bottles of beer on the wall,$" bottles.out; then
    echo "ok - script first verse"
else
    echo "FAIL: first verse missing"
    fails=$((fails+1))
fi
if grep -q "^1 bottles of beer on the wall!" bottles.out; then
    echo "ok - loop decremented to final verse"
else
    echo "FAIL: final verse missing"
    fails=$((fails+1))
fi
if grep -q "^done$" bottles.out; then
    echo "ok - script terminator"
else
    echo "FAIL: terminator missing"
    fails=$((fails+1))
fi

if [ "$fails" -eq 0 ]; then
    echo "zrc consumer test: PASS"
    exit 0
fi
echo "zrc consumer test: $fails FAILURES"
echo "--- bottles.out ---"; cat bottles.out
echo "--- bottles.err ---"; cat bottles.err
exit 1
