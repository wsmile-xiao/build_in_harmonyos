#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the fastahack CLI executable
# Runs in conanrun env (PATH includes installed bin/).
set -euo pipefail

echo "[test] fastahack prints usage when no FASTA file is given"
# || true: 无参数时 fastahack 预期以非零码退出（上游行为），
# 我们捕获输出并由下一条 grep 断言 usage 横幅（不是吞错）。
out=$(fastahack 2>&1 || true)
echo "$out" | grep -q "usage: fastahack" && echo "OK: usage banner" || {
    echo "FAIL: fastahack did not print usage banner"
    echo "$out"
    exit 1
}

echo "[test] fastahack generates a FASTA index (.fai) and extracts a known subsequence"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
cp correct.fasta "$tmpdir/ref.fasta"

fastahack -i "$tmpdir/ref.fasta"
[ -f "$tmpdir/ref.fasta.fai" ] && echo "OK: index file generated" || {
    echo "FAIL: .fai index file not produced"
    exit 1
}

# correct.fasta: sequence 1 is a well-known TAACCCTA... repeat; first 20 bases:
expected="TAACCCTAACCCTAACCCTA"
got=$(fastahack -r 1:1..20 "$tmpdir/ref.fasta")
echo "  got: $got"
[ "$got" = "$expected" ] && echo "OK: subsequence extraction matches upstream sequence" || {
    echo "FAIL: extracted sequence mismatch (expected $expected)"
    exit 1
}

echo "[test] fastahack -e entropy returns a numeric value"
ent=$(fastahack -e -r 1:1..20 "$tmpdir/ref.fasta")
echo "  entropy: $ent"
case "$ent" in
    ''|*[!0-9.]*) echo "FAIL: entropy not numeric ($ent)"; exit 1 ;;
    *) echo "OK: entropy numeric: $ent" ;;
esac

echo "[test] fastahack -d dump prints header-tab-sequence rows"
dump=$(fastahack -d "$tmpdir/ref.fasta")
echo "$dump" | grep -q $'^1\t' && echo "OK: dump row for seq 1" || {
    echo "FAIL: dump did not produce '1<TAB>...' row"
    echo "$dump" | head -3
    exit 1
}

echo "All fastahack tests passed."
