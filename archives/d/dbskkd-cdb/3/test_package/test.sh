#!/usr/bin/env bash
# test_package/test.sh — consumer tests for the packaged dbskkd-cdb 3.00 (OHOS aarch64).
#
# Usage: bash test.sh <package_bin_dir> <cdb_tools_bin_dir>
#
# The binary under test is always taken from the tested package's bin/ directory
# (never from PATH), so the CI L1e negative test — package artifacts removed and
# the test re-run — genuinely fails.
#
# Upstream 3.00 ships no test suite at all: the release tarball contains no
# test/check member, the Makefile has only all/clean/dbskkd-cdb/install targets
# and .travis.yml runs nothing but `make`. Every case below is therefore a
# consumer-side functional case added by this adaptation. They drive the real
# SKK server protocol: start dbskkd-cdb on a dictionary, send a request on
# stdin, compare the exact answer bytes on stdout and the exit status.
#
# The dictionary is a cdb binary database, so it is NOT committed (the CI
# checkout-pr step cannot apply a PR diff carrying new binary files); it is
# rebuilt here from the committed plain-text SKK-JISYO fixture by
# fixtures/make_dict.py, which uses cdbmake from the cdb package — the
# reference writer of the library the server links against.
set -euo pipefail

BIN_DIR="${1:-}"
CDB_BIN_DIR="${2:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "[fail] dbskkd-cdb: package bin dir not found: '$BIN_DIR'"
    exit 1
fi
if [ -z "$CDB_BIN_DIR" ] || [ ! -d "$CDB_BIN_DIR" ]; then
    echo "[fail] dbskkd-cdb: cdb tools bin dir not found: '$CDB_BIN_DIR'"
    exit 1
fi

SERVER="$BIN_DIR/dbskkd-cdb"
if [ ! -f "$SERVER" ]; then
    echo "[fail] dbskkd-cdb: binary missing in package: $SERVER"
    exit 1
fi
if [ ! -x "$SERVER" ]; then
    echo "[fail] dbskkd-cdb: binary is not executable: $SERVER"
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
FIXTURES="$HERE/fixtures"
GOLDEN_CDBMAKE="$FIXTURES/SKK-JISYO.test.cdbmake"

for tool in "make_dict.py" "session_check.py" "ohos_platform_check.py" "SKK-JISYO.test" "SKK-JISYO.alt"; do
    if [ ! -f "$FIXTURES/$tool" ]; then
        echo "[fail] dbskkd-cdb: missing test fixture: $FIXTURES/$tool"
        exit 1
    fi
done
if ! command -v python3 > /dev/null 2>&1; then
    echo "[fail] dbskkd-cdb: python3 is required by the test fixtures and is not available"
    exit 1
fi
if [ ! -x "$CDB_BIN_DIR/cdbmake" ] || [ ! -x "$CDB_BIN_DIR/cdbtest" ]; then
    echo "[fail] dbskkd-cdb: cdbmake/cdbtest not executable in '$CDB_BIN_DIR'"
    exit 1
fi

# Work OUTSIDE the source tree whenever the platform allows it (CI workers have
# a writable /tmp, the OHOS device does not), so that a killed run can never
# leave generated .cdb files inside the packaging checkout.
WORK_DIR="$(mktemp -d 2>/dev/null || true)"
if [ -z "$WORK_DIR" ] || [ ! -d "$WORK_DIR" ]; then
    WORK_DIR="$HERE/dbskkd-cdb-test-work"
    rm -rf "$WORK_DIR"
    mkdir -p "$WORK_DIR"
fi
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM
echo "[step] dbskkd-cdb: work directory: $WORK_DIR"

DICT="$WORK_DIR/SKK-JISYO.test.cdb"
ALT_DICT="$WORK_DIR/SKK-JISYO.alt.cdb"
if ! python3 "$FIXTURES/make_dict.py" "$FIXTURES/SKK-JISYO.test" "$DICT" "$CDB_BIN_DIR"; then
    echo "[fail] dbskkd-cdb: dictionary generation failed: $DICT"
    exit 1
fi
if ! python3 "$FIXTURES/make_dict.py" "$FIXTURES/SKK-JISYO.alt" "$ALT_DICT" "$CDB_BIN_DIR"; then
    echo "[fail] dbskkd-cdb: alternative dictionary generation failed: $ALT_DICT"
    exit 1
fi

TOTAL=0
PASSED=0
FAILED=0

ok() {
    TOTAL=$((TOTAL + 1))
    PASSED=$((PASSED + 1))
    echo "        [ok] $1"
}

ko() {
    TOTAL=$((TOTAL + 1))
    FAILED=$((FAILED + 1))
    echo "        [fail] $1"
    if [ -n "${2:-}" ] && [ -f "$2" ]; then
        sed -n '1,20p' "$2"
    fi
}

# Run the packaged server once with the request in <file> as stdin.
# $1 = dictionary, $2 = file holding the request bytes.
# Exit status ends up in RUN_RC, stdout in actual.out, stderr in actual.err.
run_server() {
    local dict="$1" request_file="$2"
    set +e
    "$SERVER" "$dict" < "$request_file" > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
    RUN_RC=$?
    set -e
}

# One request / one answer case: exact stdout bytes and exact exit status.
# $1 = case name, $2 = request bytes, $3 = expected stdout, $4 = expected rc.
case_request() {
    local name="$1" request="$2" expected="$3" expect_rc="$4"
    printf '%s' "$request" > "$WORK_DIR/request.bin"
    printf '%s' "$expected" > "$WORK_DIR/expected.out"
    run_server "$DICT" "$WORK_DIR/request.bin"
    if [ "$RUN_RC" -ne "$expect_rc" ]; then
        ko "$name: exit status $RUN_RC (expected $expect_rc)" "$WORK_DIR/actual.err"
        return
    fi
    if cmp -s "$WORK_DIR/expected.out" "$WORK_DIR/actual.out"; then
        ok "$name: rc=$expect_rc, stdout $(wc -c < "$WORK_DIR/actual.out" | tr -d ' ') bytes match"
    else
        ko "$name: stdout differs from the expected answer" "$WORK_DIR/actual.out"
    fi
}

echo "[step] dbskkd-cdb test_package: running against $SERVER"

# ── Cases 1-6: request codes, replies and exit statuses ──────────────────────
# '2' is the VERSION request; the answer is the version string compiled in by
# upstream ("dbskkd-cdb-3.00 " with a trailing space) and therefore also ties
# the packaged artifact to the upstream release it was built from.
case_request "version_request" "2" "dbskkd-cdb-3.00 " 0
# '3' is the HOST request; upstream always answers the constant dummy name.
case_request "host_request" "3" "novalue: " 0
# '0' is CLIENT_END: the server stops and exits successfully.
case_request "end_request" "0" "" 0
# EOF without any request is a normal shutdown (EX_OK).
case_request "eof_request" "" "" 0
# An unknown request code is a protocol error (EX_PROTOCOL == 76).
case_request "unknown_request_code" "9" "" 76
# REQUEST without a key/space separator is a protocol error (EX_PROTOCOL == 76).
case_request "malformed_request_no_space" "1x" "" 76

# ── Cases 7-11: dictionary lookups through the SKK protocol ──────────────────
# Found: SERVER_FOUND '1' + the cdb data + LF.
case_request "lookup_okuri_nasi_single" "1かんじ " $'1/漢字/\n' 0
# Found with several candidates in one cdb record.
case_request "lookup_okuri_nasi_multiple" "1あい " $'1/愛/相/\n' 0
# okuri-ari entry (key ends with the okurigana letter).
case_request "lookup_okuri_ari" "1おくr " $'1/送/\n' 0
# Miss: SERVER_NOT_FOUND '4' + the key echoed back + LF (skkinput needs it).
case_request "lookup_not_found_ascii" "1not-in-dict " $'4not-in-dict\n' 0
case_request "lookup_not_found_multibyte" "1みつからない " $'4みつからない\n' 0

# ── Case 12: a long key stays within the protocol buffer (BUFSIZE == 1024) ───
LONG_KEY="$(printf 'a%.0s' {1..64})"
case_request "lookup_long_key" "1$LONG_KEY " "4$LONG_KEY"$'\n' 0

# ── Case 13: only the first space terminates the key ─────────────────────────
case_request "lookup_trailing_text_after_key" "1かんじ extra" $'1/漢字/\n' 0

# ── Case 14: every entry of the fixture dictionary resolves exactly ──────────
COVERAGE_TOTAL=0
COVERAGE_OK=0
while IFS='|' read -r cov_key cov_data; do
    [ -n "$cov_key" ] || continue
    COVERAGE_TOTAL=$((COVERAGE_TOTAL + 1))
    printf '1%s ' "$cov_key" > "$WORK_DIR/request.bin"
    printf '1%s\n' "$cov_data" > "$WORK_DIR/expected.out"
    run_server "$DICT" "$WORK_DIR/request.bin"
    if [ "$RUN_RC" -eq 0 ] && cmp -s "$WORK_DIR/expected.out" "$WORK_DIR/actual.out"; then
        COVERAGE_OK=$((COVERAGE_OK + 1))
    else
        echo "        [info] coverage miss: key=$cov_key rc=$RUN_RC"
    fi
done <<'COVERAGE'
おくr|/送/
かえr|/帰/返/
あい|/愛/相/
かんじ|/漢字/
すずき|/鈴木/
にほん|/日本/二本/
とうきょう|/東京/
でんわ|/電話/
ほん|/本/書/
みず|/水/
COVERAGE
if [ "$COVERAGE_TOTAL" -eq 10 ] && [ "$COVERAGE_OK" -eq 10 ]; then
    ok "dictionary_coverage: $COVERAGE_OK/$COVERAGE_TOTAL fixture entries answered exactly"
else
    ko "dictionary_coverage: $COVERAGE_OK/$COVERAGE_TOTAL fixture entries answered exactly"
fi

# ── Cases 15-16: runtime dictionary selection (patch 0001) ───────────────────
# DBSKKD_JISYO alone selects the dictionary — no command line argument.
printf '1かんじ ' > "$WORK_DIR/request.bin"
printf '1/幹事/\n' > "$WORK_DIR/expected.out"
set +e
DBSKKD_JISYO="$ALT_DICT" "$SERVER" < "$WORK_DIR/request.bin" \
    > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
RUN_RC=$?
set -e
if [ "$RUN_RC" -eq 0 ] && cmp -s "$WORK_DIR/expected.out" "$WORK_DIR/actual.out"; then
    ok "dictionary_env_var: DBSKKD_JISYO alone selected the alternate dictionary (1/幹事/)"
else
    ko "dictionary_env_var: rc=$RUN_RC, answer does not come from the alternate dictionary" "$WORK_DIR/actual.out"
fi

# argv[1] wins over DBSKKD_JISYO, and the compiled-in default stays a fallback.
printf '1かんじ ' > "$WORK_DIR/request.bin"
printf '1/漢字/\n' > "$WORK_DIR/expected.out"
set +e
DBSKKD_JISYO="$ALT_DICT" "$SERVER" "$DICT" < "$WORK_DIR/request.bin" \
    > "$WORK_DIR/actual.out" 2> "$WORK_DIR/actual.err"
RUN_RC=$?
set -e
if [ "$RUN_RC" -eq 0 ] && cmp -s "$WORK_DIR/expected.out" "$WORK_DIR/actual.out"; then
    ok "argv_overrides_env_var: argv[1] dictionary won over DBSKKD_JISYO (1/漢字/)"
else
    ko "argv_overrides_env_var: rc=$RUN_RC, argv[1] did not take precedence" "$WORK_DIR/actual.out"
fi

# ── Case 17: an unusable dictionary is a configuration error (EX_CONFIG == 78)
printf '2' > "$WORK_DIR/request.bin"
run_server "$WORK_DIR/does-not-exist.cdb" "$WORK_DIR/request.bin"
if [ "$RUN_RC" -eq 78 ] && [ ! -s "$WORK_DIR/actual.out" ]; then
    ok "missing_dictionary_exit_code: rc=78 with no stdout"
else
    ko "missing_dictionary_exit_code: rc=$RUN_RC (expected 78) with $(wc -c < "$WORK_DIR/actual.out" | tr -d ' ') stdout bytes" "$WORK_DIR/actual.err"
fi

# ── Case 18: the upstream compiled-in dictionary path is still the default ───
if python3 -c '
import sys
blob = open(sys.argv[1], "rb").read()
sys.exit(0 if b"/usr/local/share/skk/SKK-JISYO.L.cdb" in blob else 1)
' "$SERVER"; then
    ok "default_dictionary_path_baked_in: upstream JISYO_FILE default present in the binary"
else
    ko "default_dictionary_path_baked_in: upstream JISYO_FILE default missing from the binary"
fi

# ── Case 19: the generated cdbmake input matches the committed golden text ───
if cmp -s "$GOLDEN_CDBMAKE" "$DICT.cdbmake"; then
    ok "cdbmake_input_matches_golden: generated input identical to fixtures/SKK-JISYO.test.cdbmake"
else
    ko "cdbmake_input_matches_golden: generated input differs from the golden file" "$DICT.cdbmake"
fi

# ── Case 20: the fixture is validated by the reference cdb reader ────────────
set +e
"$CDB_BIN_DIR/cdbtest" < "$DICT" > "$WORK_DIR/cdbtest.out" 2>&1
CDBTEST_RC=$?
set -e
CDBTEST_MISSING=0
for expected_line in "found: 10" "different record: 0" "bad length: 0" "not found: 0" "untested: 0"; do
    grep -qF "$expected_line" "$WORK_DIR/cdbtest.out" || CDBTEST_MISSING=$((CDBTEST_MISSING + 1))
done
if [ "$CDBTEST_RC" -eq 0 ] && [ "$CDBTEST_MISSING" -eq 0 ]; then
    ok "cdb_fixture_reference_reader: cdbtest reports 10 found and 0 in every other category"
else
    ko "cdb_fixture_reference_reader: rc=$CDBTEST_RC, $CDBTEST_MISSING expected counters missing" "$WORK_DIR/cdbtest.out"
fi

# ── Cases 21-26: one interactive session through the request loop ────────────
set +e
python3 "$FIXTURES/session_check.py" "$SERVER" "$DICT" argv > "$WORK_DIR/session.out" 2>&1
SESSION_RC=$?
set -e
SESSION_CHECKS=0
while IFS='|' read -r tag name status detail; do
    [ "$tag" = "CHECK" ] || continue
    SESSION_CHECKS=$((SESSION_CHECKS + 1))
    if [ "$status" = "OK" ]; then
        ok "$name: $detail"
    else
        ko "$name: $detail" "$WORK_DIR/session.out"
    fi
done < "$WORK_DIR/session.out"
if [ "$SESSION_CHECKS" -eq 0 ]; then
    ko "interactive_session: driver produced no check lines (rc=$SESSION_RC)" "$WORK_DIR/session.out"
fi

# ── Cases 27-31: HarmonyOS-specific platform checks on the shipped artifact ──
# Five checks that a plain Linux build of the same source does not have to
# satisfy: the OHOS loader requires a signed image (.codesign), the platform L4
# baseline (PIE + NX + RELRO + BIND_NOW), a relocatable libc-only dependency
# set, and deployment on a device where the system data directories are
# read-only and no build-time environment exists. See the fixture docstring.
set +e
python3 "$FIXTURES/ohos_platform_check.py" "$SERVER" "$DICT" "$WORK_DIR" > "$WORK_DIR/ohos.out" 2>&1
OHOS_RC=$?
set -e
OHOS_CHECKS=0
while IFS='|' read -r tag name status detail; do
    [ "$tag" = "CHECK" ] || continue
    OHOS_CHECKS=$((OHOS_CHECKS + 1))
    if [ "$status" = "OK" ]; then
        ok "$name: $detail"
    else
        ko "$name: $detail" "$WORK_DIR/ohos.out"
    fi
done < "$WORK_DIR/ohos.out"
if [ "$OHOS_CHECKS" -ne 5 ]; then
    ko "ohos_platform_checks: expected 5 platform checks, got $OHOS_CHECKS (rc=$OHOS_RC)" "$WORK_DIR/ohos.out"
fi

echo "[step] dbskkd-cdb test_package summary: TOTAL=$TOTAL PASS=$PASSED FAIL=$FAILED"
if [ "$TOTAL" -eq 0 ] || [ "$FAILED" -ne 0 ]; then
    echo "[fail] dbskkd-cdb test_package: $FAILED of $TOTAL cases failed"
    exit 1
fi
echo "[ok] dbskkd-cdb test_package: all $TOTAL cases passed"
