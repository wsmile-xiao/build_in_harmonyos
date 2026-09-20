#!/bin/sh
# minibwa 0.4 test_package 测试源文件（L0c 门禁识别 .sh）。
# 真实验证安装产物（R34 反空壳），全部检查都执行被测包的 bin/minibwa：
#   1. bin/minibwa 存在、可执行且为 ELF（od 读 magic，headless 环境无 file 命令）
#   2. CLI 子命令：--help 输出 usage、version 输出 0.4
#   3. index→map 全流程：确定性 tiny 数据集（168bp 参考序列 + 100bp 精确子串读段），
#      SAM 断言 RNAME=tiny / POS=21 / CIGAR=100M / NM:i:0 / 非次级比对
# 用法：sh test_minibwa.sh <安装包 bin 目录>
set -u

BIN_DIR="${1:?usage: test_minibwa.sh <package bin dir>}"
BIN="$BIN_DIR/minibwa"
WORK="$PWD/.minibwa-test-work"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FAIL: cannot create $WORK" >&2; exit 1; }

fail() {
    echo "FAIL: $*" >&2
    if [ -d "$WORK" ]; then
        ls -l "$WORK" >&2 2>/dev/null
        for f in "$WORK"/*.log "$WORK"/*.err "$WORK"/map.sam; do
            [ -f "$f" ] && { echo "--- $f ---" >&2; tail -n 5 "$f" >&2; }
        done
    fi
    exit 1
}

# 1) 安装产物存在 + 可执行 + ELF magic (\x7fELF)
[ -f "$BIN" ] || fail "missing installed binary: $BIN"
[ -x "$BIN" ] || fail "installed binary not executable: $BIN"
magic=$(od -An -tx1 -N4 "$BIN" 2>/dev/null | tr -d ' \n')
[ "$magic" = "7f454c46" ] || fail "minibwa is not an ELF binary (magic=$magic)"

# 2) CLI 子命令
"$BIN" --help > "$WORK/help.txt" 2>&1 \
    || fail "minibwa --help exited non-zero"
grep -q "Usage: minibwa" "$WORK/help.txt" \
    || fail "--help output missing usage text: $(head -n 2 "$WORK/help.txt")"
"$BIN" version > "$WORK/version.txt" 2>&1 \
    || fail "minibwa version exited non-zero"
grep -q "0.4" "$WORK/version.txt" \
    || fail "unexpected version output: $(cat "$WORK/version.txt")"

# 3) index→map 全流程（与 test_package/conanfile.py 同一确定性数据集）
cat > "$WORK/tiny-ref.fa" <<'EOF'
>tiny
ACGTGCAATGTCAGTCAAGTCAGTTGACGATCGATCGTACGTAGCTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCGATCGTACGATCGATCGTACGATCGTACGATCGTACGATCGTACGATCGTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCG
EOF
READ=$(sed -n '2p' "$WORK/tiny-ref.fa" | cut -c 21-120)
READ_LEN=$(printf '%s' "$READ" | wc -c | tr -d ' ')
[ "$READ_LEN" = "100" ] || fail "read extraction got ${READ_LEN}bp, expected 100"
QUAL=$(awk 'BEGIN { for (i = 0; i < 100; i++) printf "F" }')
printf '@r1\n%s\n+\n%s\n' "$READ" "$QUAL" > "$WORK/tiny-read.fq"

"$BIN" index "$WORK/tiny-ref.fa" > "$WORK/index.log" 2>&1 \
    || fail "minibwa index exited non-zero: $(tail -n 3 "$WORK/index.log")"
[ -f "$WORK/tiny-ref.fa.mbw" ] || [ -f "$WORK/tiny-ref.fa.l2b" ] \
    || fail "index produced no .mbw/.l2b files in $WORK"

"$BIN" map "$WORK/tiny-ref.fa" "$WORK/tiny-read.fq" \
    > "$WORK/map.sam" 2> "$WORK/map.err" \
    || fail "minibwa map exited non-zero: $(tail -n 3 "$WORK/map.err")"

# SAM 断言：非 @ 头记录中存在 RNAME=tiny POS=21 CIGAR=100M NM:i:0 的主比对
# （0x100 次级比对位用纯算术判断，避免 awk and() 的可移植性问题）
awk 'BEGIN { ok = 0 }
     !/^@/ && $3 == "tiny" && $4 == 21 && $6 == "100M" && ($2 % 512) < 256 {
         for (i = 12; i <= NF; i++)
             if ($i == "NM:i:0") { ok = 1; break }
     }
     END { exit ok ? 0 : 1 }' "$WORK/map.sam" \
    || fail "no primary 100M NM:i:0 SAM record on RNAME tiny POS 21: $(grep -v '^@' "$WORK/map.sam" | head -n 1)"

rm -rf "$WORK"
echo "OK: minibwa test_package passed ($BIN)"
exit 0
