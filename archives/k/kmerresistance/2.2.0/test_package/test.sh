#!/data/service/hnp/bin/bash
# test_package/test.sh - functional smoke test for kmerresistance
# Runs in conanrun env. Usage: test.sh <path-to-kmerresistance>
set -eu

BIN="$1"
WORK="$(mktemp -d "${TMPDIR:-$PWD}/kmerresistance-test-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
PASS=0
TOTAL=7

# 1. Version banner (-v prints to stderr)
V="$("$BIN" -v 2>&1)"
echo "$V"
[ "$V" = "KmerResistance-2.2.0" ] && PASS=$((PASS+1)) || { echo "FAIL: version mismatch"; exit 1; }

# 2. Help message (-h)
H="$("$BIN" -h 2>&1)" || true
echo "$H" | grep -q "Options are:" && PASS=$((PASS+1)) || { echo "FAIL: no help"; exit 1; }

# 3. Missing-argument validation exits non-zero with help
if "$BIN" >/dev/null 2>&1; then echo "FAIL: should reject empty args"; exit 1; fi
PASS=$((PASS+1))

# 4-7. Full pipeline with stub kma (KMA is an external runtime dependency,
#       not bundled with kmerresistance upstream)
mkdir -p bin
cat > bin/kma <<'KMAEOF'
#!/data/service/hnp/bin/bash
# stub kma: emit fixed .spa/.res fixtures (mimics real KMA output format)
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "-o" ] && out="$a"
  prev="$a"
done
[ -z "$out" ] && exit 1
printf '#Template\tScore\tExpected\tTemplate_length\tQuery_Coverage\tTemplate_Coverage\tDepth\tq_value\tp_value\n' > "$out.spa"
printf 'speciesA\t100\t1e-10\t1500\t0.90\t0.95\t5.00\t0\t1\n' >> "$out.spa"
printf '#Template\tScore\tExpected\tTemplate_length\tTemplate_ID\tTemplate_Coverage\tQuery_ID\tQuery_Coverage\tDepth\tq_value\tp_value\n' > "$out.res"
printf 'geneX\t120\t1e-12\t900\t99.50\t0.98\t99.20\t0.97\t4.50\t0\t1\n' >> "$out.res"
exit 0
KMAEOF
chmod +x bin/kma
printf '@r1\nACGTACGTAC\n+\nIIIIIIIIII\n' > reads.fq

# 4. Pipeline runs to completion
PATH="$PWD/bin:$PATH" "$BIN" -i reads.fq -o out -t_db templates -s_db species > pipeline.log 2>&1 \
  && PASS=$((PASS+1)) || { echo "FAIL: pipeline"; cat pipeline.log; exit 1; }
grep -q "# DONE" pipeline.log && PASS=$((PASS+1)) || { echo "FAIL: no DONE marker"; exit 1; }

# 6. Species correlation present in output
grep -q "speciesA" out.KmerRes && PASS=$((PASS+1)) || { echo "FAIL: species missing"; exit 1; }

# 7. Gene result present with expected identity
grep -q "geneX" out.res && PASS=$((PASS+1)) || { echo "FAIL: gene missing"; exit 1; }

echo "[test] kmerresistance functional assertions: $PASS/$TOTAL passed"
[ "$PASS" -eq "$TOTAL" ]
