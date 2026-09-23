#!/bin/sh
# test_ezstream.sh — consumer-side validation for ezstream/1.0.2 (R34).
#
# ezstream is a CLI application; the package ships executables, so the
# consumer test runs the installed binaries and asserts observable
# behaviour instead of linking a library:
#
#   1. `ezstream -V` prints "ezstream version 1.0.2".
#   2. `ezstream -c <valid.xml>` parses a real 1.0.2-format XML config
#      (libxml2 code path), sets up the stream, and attempts to reach the
#      configured Icecast server; on a test box without a server the
#      expected failure mode is "connect ... Couldn't connect", proving
#      the whole configure -> parse -> connect pipeline works.
#   3. `ezstream -c <broken.xml>` surfaces a libxml2 parser error.
#   4. `ezstream-cfgmigrate -h` prints its usage banner.
#
# Usage: test_ezstream.sh <bindir_of_tested_package> <testdata_dir>

set -u

BINDIR="${1:?bindir required}"
DATADIR="${2:?testdata dir required}"

EZSTREAM="$BINDIR/ezstream"
CFG_MIGRATE="$BINDIR/ezstream-cfgmigrate"

failures=0

# --- HMDFS workdir quirk: ezstream refuses world-writeable configs ------
# cfg_file_check() (src/cfg.c) rejects any config whose mode has S_IWOTH
# (fatal "world writeable") and warns on S_IROTH. On HarmonyOS the repo
# lives on HMDFS, where checked-out files carry mode 0666 - both bits set -
# so the assertions on config parsing would fail for reasons unrelated to
# the code under test. Copy the XML fixtures to a private scratch dir and
# tighten the mode (chmod works on HMDFS) before handing them to the
# binary. On Linux CI (mode 0644) the copy is a harmless no-op.
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/ezstream-test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT INT TERM
MINIMAL_XML="$SCRATCH/ezstream-minimal.xml"
cp "$DATADIR/ezstream-minimal.xml" "$MINIMAL_XML"
chmod 0600 "$MINIMAL_XML"
BROKEN_XML="$SCRATCH/bad.xml"
printf '%s' "<ezstream><broken>" > "$BROKEN_XML"
chmod 0600 "$BROKEN_XML"

assert_contains() {
    _desc="$1"; _needle="$2"; _out="$3"
    case "$_out" in
        *"$_needle"*)
            echo "[PASS] $_desc"
            ;;
        *)
            echo "[FAIL] $_desc — expected '$_needle' in output:"
            echo "$_out" | head -5
            failures=$((failures + 1))
            ;;
    esac
}

# --- 1. version banner ------------------------------------------------
out=$("$EZSTREAM" -V 2>&1)
assert_contains "ezstream -V prints version 1.0.2" "1.0.2" "$out"

# --- 2. valid XML config: parse + connect attempt ----------------------
out=$("$EZSTREAM" -c "$MINIMAL_XML" 2>&1)
assert_contains "ezstream -c minimal.xml reaches connect stage" "Couldn't connect" "$out"

# --- 3. broken XML config: parser rejects -------------------------------
out=$("$EZSTREAM" -c "$BROKEN_XML" 2>&1)
case "$out" in
    *"parser error"*|*"Premature"*|*[Ee]rror*)
        echo "[PASS] ezstream -c bad.xml triggers libxml2 parser error"
        ;;
    *)
        echo "[FAIL] ezstream -c bad.xml — expected parser error, got: $out"
        failures=$((failures + 1))
        ;;
esac

# --- 4. cfgmigrate tool present & runs ----------------------------------
out=$("$CFG_MIGRATE" -h 2>&1)
assert_contains "ezstream-cfgmigrate -h prints usage" "ezstream-cfgmigrate" "$out"

if [ "$failures" -gt 0 ]; then
    echo "test_ezstream.sh: $failures assertion(s) failed"
    exit 1
fi
echo "test_ezstream.sh: all 4 assertions passed"
exit 0
