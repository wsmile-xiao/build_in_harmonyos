#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for the `gsasl` program.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

command -v gsasl >/dev/null || { echo "gsasl is not on PATH"; exit 1; }
echo "[test] gsasl found: $(command -v gsasl)"

# /tmp is read-only on OHOS - use a scratch dir under $HOME instead.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/libgsasl-tools-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# 1) --version / --help contract.  Both are handled by gsasl.c itself (the
#    gengetopt parser is generated with --no-handle-version --no-handle-help),
#    and both must exit 0 for the platform L2 smoke test.
echo "[test] gsasl --version"
VERSION_OUT="$(gsasl --version 2>&1)"
case "$VERSION_OUT" in
    *2.2.4*) echo "        [ok] $VERSION_OUT" ;;
    *) echo "gsasl --version did not report 2.2.4: $VERSION_OUT"; exit 1 ;;
esac

echo "[test] gsasl --help"
gsasl --help > "$TESTDIR/help.txt" 2>&1
[ -s "$TESTDIR/help.txt" ] || { echo "gsasl --help produced no output"; exit 1; }
grep -q -- "--client-mechanisms" "$TESTDIR/help.txt" || {
    echo "gsasl --help does not describe --client-mechanisms"; exit 1; }
echo "        [ok] help lists the real option table"

# 2) Bare invocation must print the usage and succeed (gsasl.c returns
#    EXIT_SUCCESS after cmdline_parser_print_help()).
echo "[test] gsasl (no arguments)"
gsasl > "$TESTDIR/bare.txt" 2>&1
[ -s "$TESTDIR/bare.txt" ] || { echo "bare gsasl produced no output"; exit 1; }
echo "        [ok] bare invocation exits 0 with usage text"

# 3) Mechanism inventory: the library is linked in and its mechanism registry
#    is reachable.  SCRAM is built into libgsasl and always available.
echo "[test] gsasl --client-mechanisms"
CLIENT_MECHS="$(gsasl --client-mechanisms 2>/dev/null)"
[ -n "$CLIENT_MECHS" ] || { echo "no client mechanisms were listed"; exit 1; }
case " $CLIENT_MECHS " in
    *" SCRAM-SHA-256 "*) ;;
    *) echo "SCRAM-SHA-256 missing from: $CLIENT_MECHS"; exit 1 ;;
esac
set -- $CLIENT_MECHS
[ "$#" -ge 5 ] || { echo "only $# client mechanisms: $CLIENT_MECHS"; exit 1; }
echo "        [ok] $# client mechanisms, includes SCRAM-SHA-256"

echo "[test] gsasl --server-mechanisms"
SERVER_MECHS="$(gsasl --server-mechanisms 2>/dev/null)"
[ -n "$SERVER_MECHS" ] || { echo "no server mechanisms were listed"; exit 1; }
case " $SERVER_MECHS " in
    *" SCRAM-SHA-256 "*) ;;
    *) echo "SCRAM-SHA-256 missing from: $SERVER_MECHS"; exit 1 ;;
esac
echo "        [ok] server mechanism list is populated"

# 4) --mkpasswd: a fixed salt and iteration count make the key derivation
#    fully deterministic, which exercises the real PBKDF2 implementation
#    inside the library rather than just the argument parser.
SALT="AAECAwQFBgcICQoLDA0ODw=="
echo "[test] gsasl --mkpasswd --mechanism SCRAM-SHA-256"
KS256="$(gsasl --mkpasswd --mechanism SCRAM-SHA-256 --password secret \
    --salt "$SALT" --iteration-count 4096 2>/dev/null)"
case "$KS256" in
    "{SCRAM-SHA-256}4096,$SALT,"*) ;;
    *) echo "unexpected mkpasswd output: $KS256"; exit 1 ;;
esac
FIELDS="$(printf '%s' "$KS256" | awk -F, '{print NF}')"
[ "$FIELDS" -eq 4 ] || { echo "expected 4 comma separated fields, got $FIELDS: $KS256"; exit 1; }
echo "        [ok] $FIELDS fields, iteration count honoured"

echo "[test] gsasl --mkpasswd is deterministic"
KS256B="$(gsasl --mkpasswd --mechanism SCRAM-SHA-256 --password secret \
    --salt "$SALT" --iteration-count 4096 2>/dev/null)"
[ "$KS256" = "$KS256B" ] || { echo "mkpasswd is not deterministic"; exit 1; }
echo "        [ok] two runs produced identical output"

echo "[test] gsasl --mkpasswd (different password must differ)"
KS256C="$(gsasl --mkpasswd --mechanism SCRAM-SHA-256 --password s3cret \
    --salt "$SALT" --iteration-count 4096 2>/dev/null)"
[ "$KS256" != "$KS256C" ] || { echo "different passwords produced the same keys"; exit 1; }
echo "        [ok] key material depends on the password"

echo "[test] gsasl --mkpasswd --mechanism SCRAM-SHA-1"
KS1="$(gsasl --mkpasswd --mechanism SCRAM-SHA-1 --password secret \
    --salt "$SALT" --iteration-count 4096 2>/dev/null)"
case "$KS1" in
    "{SCRAM-SHA-1}4096,$SALT,"*) echo "        [ok] SCRAM-SHA-1 also available" ;;
    *) echo "unexpected SCRAM-SHA-1 output: $KS1"; exit 1 ;;
esac

# 5) Negative controls.
echo "[test] gsasl --no-such-option (expected failure)"
if gsasl --no-such-option >/dev/null 2>&1; then
    echo "an unknown option was accepted"; exit 1
fi
echo "        [ok] unknown option rejected"

echo "[test] gsasl --mkpasswd --mechanism NO-SUCH-MECH (expected failure)"
if gsasl --mkpasswd --mechanism NO-SUCH-MECH --password secret \
        --salt "$SALT" >/dev/null 2>&1; then
    echo "an unknown mechanism was accepted"; exit 1
fi
echo "        [ok] unknown mechanism rejected"

# 6) The binary must be self contained: `--disable-shared` links libgsasl
#    statically, so nothing but libc may be needed at load time.  A missing
#    DT_NEEDED would not show up as a build error - only as a load failure.
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    echo "[test] $READELF -d bin/gsasl | grep NEEDED"
    NEEDED="$("$READELF" -d "$(command -v gsasl)" 2>/dev/null | grep NEEDED || true)"
    case "$NEEDED" in
        *libgsasl*) echo "gsasl still needs libgsasl: $NEEDED"; exit 1 ;;
    esac
    echo "        [ok] no libgsasl dependency${NEEDED:+ ($(printf '%s\n' "$NEEDED" | wc -l) NEEDED entries)}"
else
    echo "        [skip] no readelf on PATH"
fi

echo "All tests passed."