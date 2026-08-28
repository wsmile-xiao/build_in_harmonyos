#!/data/service/hnp/bin/bash
# test_package/test.sh — aws-lc-tools 5.2.0 consumer smoke test.
# Runs under the conanrun env (PATH includes the installed bin/).
# Every check exercises a real CLI operation of the installed binaries;
# no check may pass without actually invoking the packaged tools.
set -u

PASS=0
FAIL=0
DISCOVERED=8

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR" || exit 1

BSSL="${BSSL:-bssl}"
OSL="${OSL:-openssl}"

report() {
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        echo "[PASS] $1"
    else
        FAIL=$((FAIL + 1))
        echo "[FAIL] $1"
    fi
}

# --- 1: bssl version runs and reports --------------------------------------
out="$("$BSSL" version 2>&1)"
rc=$?
[ $rc -eq 0 ] && [ -n "$out" ]
report "bssl version (output: ${out:-<empty>})" $?

# --- 2: openssl version runs and reports ------------------------------------
out="$("$OSL" version 2>&1)"
rc=$?
[ $rc -eq 0 ] && [ -n "$out" ]
report "openssl version (output: ${out:-<empty>})" $?

# --- 3: bssl sha256sum known-answer (SHA-256("abc")) ------------------------
printf 'abc' > msg.txt
EXPECT="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
out="$("$BSSL" sha256sum msg.txt 2>&1)"
rc=$?
echo "$out" | grep -q "$EXPECT"
rc=$((rc + $?))
report "bssl sha256sum known-answer" $rc

# --- 4: openssl dgst -sha256 agrees on the same digest -----------------------
out="$("$OSL" dgst -sha256 msg.txt 2>&1)"
rc=$?
echo "$out" | grep -q "$EXPECT"
rc=$((rc + $?))
report "openssl dgst -sha256 known-answer" $rc

# --- 5: bssl rand -hex 32 yields 64 hex chars --------------------------------
out="$("$BSSL" rand -hex 32 2>/dev/null | tr -d '[:space:]')"
if [ "${#out}" -eq 64 ] && printf '%s' "$out" | grep -Eq '^[0-9a-f]{64}$'; then
    report "bssl rand -hex 32 length/alphabet" 0
else
    echo "  got: '${out}' (len=${#out})"
    report "bssl rand -hex 32 length/alphabet" 1
fi

# --- 6: bssl genrsa generates an RSA private key PEM --------------------------
"$BSSL" genrsa -bits 2048 > rsakey.pem 2>/dev/null
rc=$?
grep -q "BEGIN RSA PRIVATE KEY" rsakey.pem
rc=$((rc + $?))
report "bssl genrsa -bits 2048 writes RSA PEM key" $rc

# --- 7: openssl rsa parses the generated key ----------------------------------
"$OSL" rsa -in rsakey.pem -noout > /dev/null 2>&1
report "openssl rsa parses generated private key (-noout)" $?

# --- 8: openssl rsa exports a public key from the generated key ---------------
"$OSL" rsa -in rsakey.pem -pubout -out pubkey.pem > /dev/null 2>&1
rc=$?
[ -s pubkey.pem ]
rc=$((rc + $?))
report "openssl rsa -pubout exports non-empty public key" $rc

# --- hmbs hard-gate marker (numbers come from the counters above) ------------
passed="true"
if [ "$PASS" -ne "$DISCOVERED" ] || [ "$FAIL" -ne 0 ]; then
    passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$passed" "$DISCOVERED" "$PASS"

echo "=== test_package summary: ${PASS}/${DISCOVERED} passed, ${FAIL} failed ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$DISCOVERED" ]; then
    exit 1
fi
exit 0
