#!/data/service/hnp/bin/bash
# test_package/test.sh — real functional tests of the packaged minisign binary
# Runs in the conanrun env (PATH includes the installed bin/).
# 5 assertions: version output, key generation, signing, verification, tamper
# detection. Emits HMBS_TEST_PACKAGE_RESULT with the real counts.
set -eu

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0

# 1. version output
if minisign -v 2>&1 | grep -q "0.12"; then
    PASS=$((PASS + 1))
else
    echo "[FAIL] version output does not mention 0.12"
    FAIL=$((FAIL + 1))
fi

# 2. key generation (-W: no password prompt, non-interactive)
if minisign -G -W -s "$WORK/minisign.key" -p "$WORK/minisign.pub" >/dev/null 2>&1 \
    && [ -s "$WORK/minisign.key" ] && [ -s "$WORK/minisign.pub" ]; then
    PASS=$((PASS + 1))
else
    echo "[FAIL] key generation failed"
    FAIL=$((FAIL + 1))
fi

# 3. sign a message file
echo "minisign harmonyos test" > "$WORK/message.txt"
if minisign -S -s "$WORK/minisign.key" -m "$WORK/message.txt" >/dev/null 2>&1 \
    && [ -s "$WORK/message.txt.minisig" ]; then
    PASS=$((PASS + 1))
else
    echo "[FAIL] signing failed"
    FAIL=$((FAIL + 1))
fi

# 4. verify the signature
if minisign -V -p "$WORK/minisign.pub" -m "$WORK/message.txt" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
else
    echo "[FAIL] signature verification failed"
    FAIL=$((FAIL + 1))
fi

# 5. tamper detection: modified message must FAIL verification
echo "tampered" >> "$WORK/message.txt"
if ! minisign -V -p "$WORK/minisign.pub" -m "$WORK/message.txt" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
else
    echo "[FAIL] tampered message was accepted"
    FAIL=$((FAIL + 1))
fi

echo "minisign test_package: ${PASS} passed, ${FAIL} failed"

if [ "$FAIL" -eq 0 ]; then
    passed_json="true"
else
    passed_json="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":5,"passedCount":%s}\n' \
    "$passed_json" "$PASS"

[ "$FAIL" -eq 0 ]
