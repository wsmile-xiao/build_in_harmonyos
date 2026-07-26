#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for tpm (tiny password manager).
#
# Runs in the conanrun env, which puts the installed bin/ on PATH so `tpm`
# resolves to the packaged script.
#
# DESIGN (L1e anti-fake-test + real functional coverage)
#   The upstream tpm script has NO --help/--version flags and NO test suite.
#   Previously this file only asserted the CLI contract (USAGE line + exit 1).
#   That passed L1e but covered 0% of tpm's CORE function: insert/show of
#   encrypted passwords.
#
#   tpm's insert/show delegate to `gpg2` for symmetric encryption. The OHOS
#   artifact repo does not yet ship gpg2, so to exercise the real data path
#   we install a TEST-ONLY gpg2 stub (mock_gpg2.sh) onto PATH. This lets the
#   test drive tpm through a full insert→show round trip and assert that the
#   password written is the password read back — i.e. it verifies tpm's
#   actual job, not just that it prints a usage string.
#
#   The stub is reversible (base64), NOT real crypto; its only purpose is to
#   make gpg2-dependent code paths runnable in CI. Declared in MANIFEST.yml.

set -u

pass=0
fail=0

assert_contains() {
    # assert_contains <haystack> <needle> <label>
    if printf '%s' "$1" | grep -q -- "$2"; then
        echo "✅ $3"
        pass=$((pass + 1))
    else
        echo "❌ $3 (needle '$2' not found)"
        echo "    output was: $1"
        fail=$((fail + 1))
    fi
}

assert_eq_exit() {
    # assert_eq_exit <got> <want> <label>
    if [ "$1" -eq "$2" ]; then
        echo "✅ $3"
        pass=$((pass + 1))
    else
        echo "❌ $3 (exit $1, expected $2)"
        fail=$((fail + 1))
    fi
}

# --- setup: a temp password store + mock gpg2 on PATH ---------------------
# NOTE: setup commands use `|| exit 1` guards rather than global `set -e`,
# because the test body below intentionally captures tpm's non-zero exit codes
# into $code for assertion (a global set -e would abort on the first expected
# failure and defeat the assertions).
TEST_ROOT="${TMPDIR:-/tmp}/tpm_test_$$"
STORE_DIR="$TEST_ROOT/store"
MOCK_BIN="$TEST_ROOT/bin"
mkdir -p "$STORE_DIR" "$MOCK_BIN" || { echo "❌ setup: mkdir failed" >&2; exit 1; }

# Expose mock_gpg2.sh under the name tpm actually calls: `gpg2`.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/mock_gpg2.sh" "$MOCK_BIN/gpg2" || { echo "❌ setup: mock_gpg2.sh missing next to test.sh" >&2; exit 1; }
chmod +x "$MOCK_BIN/gpg2" || { echo "❌ setup: chmod failed" >&2; exit 1; }

export PASSWORD_STORE_DIR="$STORE_DIR"
export PATH="$MOCK_BIN:$PATH"

# Resolve the tpm executable (from conanrun PATH; fallback to which).
TPM_BIN="$(command -v tpm 2>/dev/null || true)"
if [ -z "$TPM_BIN" ]; then
    echo "❌ tpm NOT found on PATH — package did not install bin/tpm"
    fail=$((fail + 1))
else
    echo "✅ tpm found on PATH: $TPM_BIN"
    pass=$((pass + 1))
fi

# ==========================================================================
# GROUP A — CLI contract (original assertions, kept)
# ==========================================================================
echo ""
echo "--- Group A: CLI contract ---"

# A1. tpm with no args prints USAGE and exits 1
out="$($TPM_BIN 2>&1)"; code=$?
assert_contains "$out" "USAGE: tpm" "A1: no-args prints USAGE line"
assert_eq_exit "$code" 1 "A2: no-args exits 1"

# A3. unknown subcommand also prints USAGE and exits 1
out="$($TPM_BIN boguscommand 2>&1)"; code=$?
assert_contains "$out" "USAGE: tpm" "A3: unknown subcommand prints USAGE"
assert_eq_exit "$code" 1 "A4: unknown subcommand exits 1"

# ==========================================================================
# GROUP B — CORE FUNCTION: insert/show round trip (NEW)
#   This is tpm's reason to exist. Without gpg2 it was previously untested.
# ==========================================================================
echo ""
echo "--- Group B: core function (insert -> show) ---"

SECRET="correct-horse-battery-staple-789"

# B1. insert writes an encrypted entry to the store
echo "$SECRET" | $TPM_BIN insert sites/example 2>&1; code=$?
assert_eq_exit "$code" 0 "B1: insert returns 0"
# The entry file must exist at the documented store path with .gpg suffix.
if [ -f "$STORE_DIR/sites/example.gpg" ]; then
    echo "✅ B2: entry written to \$STORE/sites/example.gpg"
    pass=$((pass + 1))
else
    echo "❌ B2: entry file missing at $STORE_DIR/sites/example.gpg"
    fail=$((fail + 1))
fi
# The "ciphertext" must NOT contain the plaintext (mock still transforms it).
if grep -q "$SECRET" "$STORE_DIR/sites/example.gpg" 2>/dev/null; then
    echo "❌ B3: plaintext leaked into the entry file (not transformed)"
    fail=$((fail + 1))
else
    echo "✅ B3: entry file does not contain plaintext"
    pass=$((pass + 1))
fi

# B4. show reads back the EXACT password that was inserted (round trip)
out="$($TPM_BIN show sites/example 2>&1)"; code=$?
assert_eq_exit "$code" 0 "B4: show returns 0"
assert_contains "$out" "$SECRET" "B5: show outputs the inserted password"

# ==========================================================================
# GROUP C — error paths of the core function (NEW)
# ==========================================================================
echo ""
echo "--- Group C: error paths ---"

# C1. show a non-existent entry fails cleanly (exit 1, not a crash)
out="$($TPM_BIN show no/such/entry 2>&1)"; code=$?
assert_eq_exit "$code" 1 "C1: show-missing exits 1"
assert_contains "$out" "doesn't exist" "C2: show-missing reports absence"

# C2. insert into an existing entry is rejected (no silent overwrite)
echo "dup" | $TPM_BIN insert sites/example 2>&1 >/dev/null; code=$?
assert_eq_exit "$code" 1 "C3: insert-duplicate exits 1"

# C3. insert/show with empty entry name prints the per-command USAGE
out="$($TPM_BIN show "" 2>&1)"; code=$?
assert_contains "$out" "USAGE: tpm show" "C4: show empty-name prints USAGE"
out="$(echo x | $TPM_BIN insert "" 2>&1)"; code=$?
assert_contains "$out" "USAGE: tpm insert" "C5: insert empty-name prints USAGE"

# ==========================================================================
# Summary
# ==========================================================================
echo ""
echo "tpm functional test summary: $pass passed, $fail failed"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "All tpm tests passed."

# Clean up the temp store so repeated CI runs don't accumulate.
rm -rf "$TEST_ROOT"
