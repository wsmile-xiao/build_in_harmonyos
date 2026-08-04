#!/bin/sh
# festvox-kdlpc8k 1.4.0 — Voice data resource validation
# All 19 assertions: directory, file, non-empty, SHA256, encoding, EST header, license

V="$1"
[ -n "$V" ] || exit 1

echo "=== festvox-kdlpc8k 1.4.0 Resource Validation ==="

ok=0; fail=0

check() {
  if [ "$1" -eq 0 ]; then
    echo "[PASS] $2"; ok=$((ok+1))
  else
    echo "[FAIL] $2"; fail=$((fail+1))
  fi
}

# 1-3: Directory existence
check_dir() { [ -d "$1" ]; check $? "$2"; }
check_dir "${V}" "Dir exists: voice_root"
check_dir "${V}/festvox" "Dir exists: festvox"
check_dir "${V}/group" "Dir exists: group"

# 4-7: File existence
check_file() { [ -f "$1" ]; check $? "$2"; }
check_file "${V}/COPYING" "File exists: COPYING"
check_file "${V}/festvox/ked_diphone.scm" "File exists: ked_diphone.scm"
check_file "${V}/festvox/kddurtreeZ.scm" "File exists: kddurtreeZ.scm"
check_file "${V}/group/kedlpc8k.group" "File exists: kedlpc8k.group"

# 8-11: Non-empty (use ls -l to avoid fork issues)
for f in COPYING ked_diphone.scm kddurtreeZ.scm kedlpc8k.group; do
  sz=0
  case "$f" in
    COPYING) sz=$(ls -l "${V}/COPYING" 2>/dev/null | awk '{print $5}') ;;
    ked_diphone.scm) sz=$(ls -l "${V}/festvox/ked_diphone.scm" 2>/dev/null | awk '{print $5}') ;;
    kddurtreeZ.scm) sz=$(ls -l "${V}/festvox/kddurtreeZ.scm" 2>/dev/null | awk '{print $5}') ;;
    kedlpc8k.group) sz=$(ls -l "${V}/group/kedlpc8k.group" 2>/dev/null | awk '{print $5}') ;;
  esac
  [ -n "$sz" ] || sz=0
  [ "$sz" -gt 0 ] 2>/dev/null && echo "[PASS] Non-empty: $f (${sz} bytes)" && ok=$((ok+1)) || { echo "[FAIL] Non-empty: $f"; fail=$((fail+1)); }
done

# 12-15: SHA256 using python3
for entry in "COPYING:${V}/COPYING:7cddceb6297c6b97adf13f783473c3ad8f74452f29c5d6860f74ed6a932d5970" \
  "ked_diphone.scm:${V}/festvox/ked_diphone.scm:e31a444dbe459d49d3a863b0e5c1ee909593ce5fdd8df927ad15f5d5981dc2b6" \
  "kddurtreeZ.scm:${V}/festvox/kddurtreeZ.scm:dd72d4c8f7facfcd336c3995e2a39a97d25e068b0d5239ae83b212824b94b0c2" \
  "kedlpc8k.group:${V}/group/kedlpc8k.group:3f689e4bd6ed7a3af5d861fb26758d8e0c3c25ccd5f936745ef6614ff2d61070"; do
  fname=$(echo "$entry" | cut -d: -f1)
  fpath=$(echo "$entry" | cut -d: -f2)
  exp=$(echo "$entry" | cut -d: -f3)
  actual=$(python3 -c "
import hashlib
h = hashlib.sha256()
with open('${fpath}', 'rb') as f:
    for chunk in iter(lambda: f.read(65536), b''): h.update(chunk)
print(h.hexdigest())
" 2>/dev/null)
  [ "$actual" = "$exp" ] && echo "[PASS] SHA256 match: ${fname}" && ok=$((ok+1)) || { echo "[FAIL] SHA256 mismatch: ${fname}"; fail=$((fail+1)); }
done

# 16-17: ASCII encoding for .scm files
for f in ked_diphone.scm kddurtreeZ.scm; do
  fp="${V}/festvox/${f}"
  if python3 -c "open('${fp}','r',encoding='ascii').read();print('ok')" 2>/dev/null | grep -q ok; then
    echo "[PASS] ASCII encoding: ${f}"; ok=$((ok+1))
  else
    echo "[FAIL] ASCII encoding: ${f}"; fail=$((fail+1))
  fi
done

# 18: .group EST header signature
if python3 -c "
with open('${V}/group/kedlpc8k.group','rb') as f:
    print('ok' if f.read(14) == b'EST_File index' else 'bad')
" 2>/dev/null | grep -q ok; then
  echo "[PASS] .group EST_File index signature"; ok=$((ok+1))
else
  echo "[FAIL] .group EST_File index signature"; fail=$((fail+1))
fi

# 19: COPYING license text
if grep -q "Centre for Speech Technology Research" "${V}/COPYING" && grep -q "University of Edinburgh" "${V}/COPYING"; then
  echo "[PASS] COPYING contains CSTR Edinburgh notice"; ok=$((ok+1))
else
  echo "[FAIL] COPYING missing expected license text"; fail=$((fail+1))
fi

echo ""
echo "============================================================"
echo "Resource: ${ok}/$((ok+fail)) passed, ${fail} failed"
if [ "$fail" -gt 0 ]; then exit 1; fi
echo "[PASS] All resource assertions passed"
