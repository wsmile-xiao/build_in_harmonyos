#!/data/service/hnp/bin/bash
# test_package 静态测试源（跟踪入库；CI L0c 白名单后缀测试源）。
# conanfile.py test() 以 `bash test.sh <minimodem> <workdir>` 调用——参数传递、
# 无内插引号（conan self.run 再过一层 shell，两层嵌套引号在 toybox sh 上实测
# 报 "no closing quote"）；OHOS 上 ELF 须经 bash 包装执行（mksh 不能直接跑 ELF）。
set -e
MINIMODEM="$1"
WORKDIR="$2"

# ── 用例 1：版本自报 ──────────────────────────────
"$MINIMODEM" --version > "$WORKDIR/version.out" 2>&1
grep -q "minimodem 0.24" "$WORKDIR/version.out" || {
    echo "E: version output mismatch:" 1>&2
    cat "$WORKDIR/version.out" 1>&2
    exit 10
}
echo "version OK: $(head -1 "$WORKDIR/version.out")"

# ── 用例 2：300 波特 FSK 往返 ────────────────────
TX_TXT="$WORKDIR/tx.txt"
WAV="$WORKDIR/tx.wav"
RX_TXT="$WORKDIR/rx.txt"
printf 'minimodem 0.24 OHOS armv8 FSK roundtrip 0123456789\n%.0s' 1 2 3 4 5 6 7 8 9 10 > "$TX_TXT"
"$MINIMODEM" --tx --file "$WAV" 300 --volume 0.8 < "$TX_TXT" > /dev/null
test -s "$WAV" || { echo "E: tx produced no WAV" 1>&2; exit 11; }
"$MINIMODEM" --rx --file "$WAV" 300 > "$RX_TXT"
cmp "$TX_TXT" "$RX_TXT" || { echo "E: roundtrip mismatch" 1>&2; exit 12; }
echo "FSK 300-baud roundtrip OK: $(wc -c < "$TX_TXT") bytes identical"
