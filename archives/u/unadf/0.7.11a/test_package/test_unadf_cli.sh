#!/bin/bash
# unadf consumer test — drives the packaged library and the packaged CLI
# against one real ADF image produced by the test program itself.
set -u
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

UNADF="$(command -v unadf || true)"
if [ -z "$UNADF" ]; then no "unadf binary not on PATH"; echo "----"; echo "PASS=$PASS FAIL=$FAIL"; exit 1; fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
IMG="$WORK/test.adf"

# --- 1. library roundtrip: format an ADF, then mount it back --------------
libout=$(./test_unadf_lib "$IMG" 2>&1); lrc=$?
echo "$libout"
if [ $lrc -eq 0 ]; then ok "libadf roundtrip (format + mount) exits 0"
else no "libadf roundtrip exited $lrc"; fi
if echo "$libout" | grep -q "LIB_ASSERTIONS_OK"; then ok "libadf assertions all passed"
else no "libadf assertions did not report OK"; fi

# --- 2. the image we just wrote has the right on-disk geometry -------------
if [ -f "$IMG" ]; then
  sz=$(wc -c < "$IMG" | tr -d ' ')
  if [ "$sz" = "901120" ]; then ok "ADF is 901120 bytes (880 blocks x 2 x 512)"
  else no "ADF size $sz != 901120"; fi
else
  no "no ADF image produced"
fi

# --- 3. CLI: help must exit 0 and identify itself -------------------------
if "$UNADF" -h > "$WORK/help.txt" 2>&1; then ok "unadf -h exits 0"
else no "unadf -h exited $?"; fi
if grep -qi "unadf" "$WORK/help.txt"; then ok "help text identifies unadf"
else no "help text missing program name"; fi

# --- 4. CLI: missing input must fail non-zero -----------------------------
"$UNADF" -l /nonexistent/should-not-exist.adf >/dev/null 2>&1
if [ $? -ne 0 ]; then ok "missing input exits non-zero"; else no "missing input silently exited 0"; fi

# --- 5. CLI: list the real image and see our volume name ------------------
lout=$("$UNADF" -l "$IMG" 2>&1); lrc=$?
if [ $lrc -eq 0 ]; then ok "unadf -l on the real image exits 0"
else no "unadf -l exited $lrc"; fi
if echo "$lout" | grep -q "Empty"; then ok "CLI lists the volume name written by libadf"
else no "CLI output lacks the volume name"; fi
if echo "$lout" | grep -q "Cylinders"; then ok "CLI printed device geometry"
else no "CLI output lacks geometry line"; fi

# --- 6. CLI: recursive listing must also succeed --------------------------
rout=$("$UNADF" -r "$IMG" 2>&1); rrc=$?
if [ $rrc -eq 0 ]; then ok "unadf -r recursive listing exits 0"
else no "unadf -r exited $rrc"; fi

# --- 7. CLI: extraction to a directory ------------------------------------
mkdir -p "$WORK/out"
eout=$("$UNADF" -d "$WORK/out" -l "$IMG" 2>&1); erc=$?
if [ $erc -eq 0 ]; then ok "extraction listing exits 0"
else no "extraction listing exited $erc"; fi

echo "----"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
