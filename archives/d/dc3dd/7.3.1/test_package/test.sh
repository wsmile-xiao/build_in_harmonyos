#!/data/service/hnp/bin/bash
# Deterministic consumer smoke tests for the installed dc3dd executable.
set -euo pipefail

fail()
{
    echo "FAIL: $1"
    exit 1
}

work_root="${TMPDIR:-${HOME:-.}/tmp}/dc3dd-test-$$"
mkdir -p "$work_root"
trap 'rm -rf "$work_root"' EXIT

echo "[1/5] version"
version_output="$(dc3dd --version 2>&1 || true)"
echo "$version_output" | grep "7.3.1" >/dev/null || fail "version mismatch"

echo "[2/5] compiled hash defaults"
flags_output="$(dc3dd --flags 2>&1)"
for flag in DEFAULT_HASH_MD5 DEFAULT_HASH_SHA1 DEFAULT_HASH_SHA256 DEFAULT_HASH_SHA512
do
    echo "$flags_output" | grep "$flag" >/dev/null || fail "$flag missing"
done

echo "[3/5] file imaging and SHA-256"
input="$work_root/input.bin"
output="$work_root/output.bin"
log="$work_root/imaging.log"
printf '%s\n%s\n' \
    'dc3dd HarmonyOS smoke test' \
    '0123456789abcdef' > "$input"
dc3dd if="$input" of="$output" log="$log" hash=sha256
cmp "$input" "$output" || fail "imaged file differs"
[ -s "$log" ] || fail "log was not created"
grep "65191690c1470d86b2a8e527a4379430745d24775c3e58570763253f45ddc101" \
    "$log" >/dev/null || fail "SHA-256 digest mismatch"

echo "[4/5] split output"
split_base="$work_root/split"
joined="$work_root/joined.bin"
dc3dd if="$input" ofs="$split_base.000" ofsz=16
cat "$split_base".* > "$joined"
cmp "$input" "$joined" || fail "split output differs"

echo "[5/5] text pattern generation"
pattern="$work_root/pattern.bin"
dc3dd tpat=OHOS of="$pattern" cnt=2
pattern_size="$(wc -c < "$pattern")"
[ "$pattern_size" -eq 1024 ] || fail "pattern size is $pattern_size"

echo "PASS: dc3dd consumer smoke tests"
