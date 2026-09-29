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

# --- 7. CLI: extraction must actually write the file we stored ------------
# unadf's usage is `unadf [flags] dumpname.adf [files-with-path] [-d dir]`,
# so -d has to come AFTER the image name. Passing `-d dir -l img` makes the
# tool treat `dir` as the dump name and abort with
# "adfDevType : unknown device type" / "Can't mount the dump device".
mkdir -p "$WORK/out"
eout=$("$UNADF" -l "$IMG" -d "$WORK/out" 2>&1); erc=$?
if [ $erc -eq 0 ]; then ok "extraction listing exits 0"
else no "extraction listing exited $erc"; fi

if echo "$eout" | grep -q "roundtrip.bin"; then
  ok "listing shows the file the library wrote"
else
  no "listing lacks roundtrip.bin: $eout"
fi

# Now extract for real (no -l) and compare byte-for-byte.
mkdir -p "$WORK/x"
"$UNADF" "$IMG" -d "$WORK/x" > "$WORK/x.log" 2>&1
xrc=$?
if [ $xrc -eq 0 ]; then ok "plain extraction exits 0"; else no "plain extraction exited $xrc"; fi
if [ -f "$WORK/x/roundtrip.bin" ]; then
  ok "extraction produced roundtrip.bin"
  # 8 sectors x 512 bytes, byte i of sector s equals (s + i) mod 256.
  if python3 - "$WORK/x/roundtrip.bin" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read()
assert len(d) == 8 * 512, f"length {len(d)}"
for s in range(8):
    for i in range(512):
        if d[s * 512 + i] != (s + i) & 0xFF:
            raise SystemExit(f"mismatch at sector {s} byte {i}")
PY
  then ok "extracted bytes match what the library wrote"
  else no "extracted bytes differ from the written payload"; fi
else
  no "extraction did not produce roundtrip.bin"
fi

echo "----"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
