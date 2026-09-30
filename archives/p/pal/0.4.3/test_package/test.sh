#!/data/service/hnp/bin/bash
# test_package/test.sh -- consumer assertions for the packaged pal 0.4.3.
#
# Runs inside the Conan *run* environment: PATH contains the package bin/ and
# LD_LIBRARY_PATH contains glib/readline/ncurses.  pal is a curses calendar
# program, so only its non-interactive paths are exercised -- but every case
# below really executes the delivered ELF (which is itself the proof that the
# "do not strip on OHOS" prescription worked: a stripped binary fails to exec
# with rc 126 / "Operation not permitted" and cannot even print --version).
set -u

BIN=pal
# Scratch dir for the fake HOME (pal writes ~/.pal/pal.conf on first run).
# conanfile.py passes a temp dir *outside* the test_package tree so this script
# never leaves junk in the delivered recipe directory; fall back to $PWD only
# when somebody runs it by hand.
W="${1:-$(pwd)/paltest.$$}"
rm -rf "$W"
mkdir -p "$W/home"

if ! command -v "$BIN" >/dev/null 2>&1; then
    echo "[FAIL] '$BIN' is not on PATH in the conanrun environment"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"bash test.sh","discovered":0,"passedCount":0}'
    exit 1
fi

discovered=0
passed=0

expect() { # expect <description> <ERE> <command...>
    desc="$1"
    pat="$2"
    shift 2
    discovered=$((discovered + 1))
    out="$("$@" 2>&1)"
    rc=$?
    if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -Eq "$pat"; then
        passed=$((passed + 1))
        echo "[ok]   $desc"
    else
        echo "[FAIL] $desc (rc=$rc, expected /$pat/)"
        printf '%s\n' "$out" | head -6
    fi
}

# 1-3: version / help surfaces.
expect "--version reports the packaged release" '^pal 0\.4\.3$' "$BIN" --version
expect "--help prints the option block"        'Display version information' "$BIN" --help
expect "-h prints the copyright banner"         'pal 0\.4\.3 - Copyright'    "$BIN" -h

# 4: the calendar really renders for a fixed date (proves readline + ncursesw +
#    glib symbols all resolve at run time, not just that the file loads).
expect "renders a month grid for -d 09/2026" 'Su[[:space:]]+Mo[[:space:]]+Tu' \
       "$BIN" --nocolor -d 09/2026

# 5: with an empty HOME, pal must fall back to the compiled-in PREFIX and read
#    the shipped share/pal/*.pal data.  This is the assertion that the delivery
#    layout (bin/pal + etc/pal.conf + share/pal/*.pal) and -DPREFIX agree.
discovered=$((discovered + 1))
HOME="$W/home" "$BIN" --nocolor -v -d 09/2026 > "$W/verbose.txt" 2>&1
rc=$?
if [ "$rc" -eq 0 ] \
   && grep -Eq 'Done reading data \([1-9][0-9]* events, 4 files\)' "$W/verbose.txt" \
   && grep -q '/share/pal/history\.pal' "$W/verbose.txt" \
   && grep -q '/share/pal/us\.pal' "$W/verbose.txt"; then
    passed=$((passed + 1))
    echo "[ok]   empty-HOME fallback reads the packaged share/pal data"
    grep -E '^Reading:|Done reading data' "$W/verbose.txt" | head -6
else
    echo "[FAIL] empty-HOME fallback did not load the packaged data (rc=$rc)"
    head -12 "$W/verbose.txt"
fi

if [ "$discovered" -gt 0 ] && [ "$passed" -eq "$discovered" ]; then
    overall=true
else
    overall=false
fi

echo "consumer assertions: ${passed}/${discovered} passed"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$overall,\"command\":\"bash test.sh\",\"discovered\":$discovered,\"passedCount\":$passed}"
[ "$overall" = "true" ] || exit 1
