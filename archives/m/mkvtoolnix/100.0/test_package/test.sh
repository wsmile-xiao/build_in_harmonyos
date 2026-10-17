#!/data/service/hnp/bin/bash
# test_package/test.sh — mkvtoolnix 安装包集成测试（R10）
#
# 内容：
#   1) 工具可用性冒烟：mkvmerge --version / mkvpropedit --version
#   2) 自生成 Matroska 集成测试（版权自由，全部字节为本测试脚本自编）：
#      - 在临时目录运行时生成一个最小合法 EBML/Matroska 文件（125 字节）
#      - 用已安装的 mkvmerge --identify 识别（必须识别为 Matroska + audio(PCM)）
#      - 用已安装的 mkvmerge 将该输入封装生成新 Matroska 文件（生成证据）
#      - 用已安装的 mkvinfo 解析生成结果（必须解析出 Document type: matroska）
#      - trap 清理临时目录；不向仓库/包内保留任何生成媒体
#
# 说明：本测试为独立本地覆盖，不代表/不替代/不声称上游 630 行为用例的
# 通过或跳过（上游 tests/data 样本含版权素材不可分发，R08 已记录）。
#
# 最小 Matroska 字节构成（自编，依据公开 EBML/Matroska 规范）：
#   EBML header: 1A45DFA3 + EBMLVersion=1 + EBMLReadVersion=1
#                + EBMLMaxIDLength=4 + EBMLMaxSizeLength=8
#                + DocType="matroska" + DocTypeVersion=4 + DocTypeReadVersion=2
#   Segment: 18538067 + SegmentInfo(TimestampScale=1000000, MuxingApp,
#            WritingApp="mkvtoolnix-test") + Tracks(1 个 Track: TrackNumber=1,
#            TrackUID=1, TrackType=2 audio, CodecID="A_PCM/INT/LIT")
set -eu

echo "[test] mkvmerge --version"
mkvmerge --version && echo "PASS: mkvmerge --version" || {
    echo "FAIL: mkvmerge --version 失败"
    exit 1
}

echo "[test] mkvpropedit --version"
mkvpropedit --version && echo "PASS: mkvpropedit --version" || {
    echo "FAIL: mkvpropedit --version 失败"
    exit 1
}

# ── 自生成 Matroska 集成测试 ──
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mkvtoolnix-test.XXXXXX")"
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

INPUT="$TEST_DIR/minimal.mkv"
OUTPUT="$TEST_DIR/output.mkv"

# 生成 125 字节极简 EBML/Matroska（自编字节，逐字节固定）
printf '\x1a\x45\xdf\xa3\xa3\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04\x42\xf3\x81\x08\x42\x82\x88matroska\x42\x87\x81\x04\x42\x85\x81\x02\x18\x53\x80\x67\xd0\x15\x49\xa9\x66\xab\x2a\xd7\xb1\x83\x0f\x42\x40\x4d\x80\x8fmkvtoolnix-test\x57\x41\x8fmkvtoolnix-test\x16\x54\xae\x6b\x9b\xae\x99\xd7\x81\x01\x73\xc5\x81\x01\x83\x81\x02\x86\x8dA_PCM/INT/LIT' > "$INPUT"

SIZE="$(stat -c %s "$INPUT" 2>/dev/null || echo 0)"
echo "[test] generated input: $INPUT ($SIZE bytes)"
[ "$SIZE" = "125" ] || { echo "FAIL: 生成输入大小异常 ($SIZE != 125)"; exit 1; }

echo "[test] mkvmerge --identify (recognition)"
IDENT_OUT="$(mkvmerge --identify "$INPUT" 2>&1)" || {
    echo "FAIL: mkvmerge --identify 退出码非 0"; echo "$IDENT_OUT"; exit 1
}
echo "$IDENT_OUT"
echo "$IDENT_OUT" | grep -q 'container: Matroska' || { echo "FAIL: 未识别为 Matroska"; exit 1; }
echo "$IDENT_OUT" | grep -q 'audio' || { echo "FAIL: 未识别 audio track"; exit 1; }
echo "PASS: mkvmerge 识别 Matroska"

echo "[test] mkvmerge generation (mux to new file)"
GEN_OUT="$(mkvmerge -o "$OUTPUT" "$INPUT" 2>&1)" || {
    echo "FAIL: mkvmerge 生成退出码非 0"; echo "$GEN_OUT"; exit 1
}
echo "$GEN_OUT" | tail -3
OUT_SIZE="$(stat -c %s "$OUTPUT" 2>/dev/null || echo 0)"
echo "[test] generated output: $OUTPUT ($OUT_SIZE bytes)"
[ "$OUT_SIZE" -gt 0 ] || { echo "FAIL: 生成输出为空"; exit 1; }
echo "PASS: mkvmerge 生成新 Matroska ($OUT_SIZE bytes)"

echo "[test] mkvinfo parse of generated file"
INFO_OUT="$(mkvinfo "$OUTPUT" 2>&1)" || {
    echo "FAIL: mkvinfo 解析退出码非 0"; echo "$INFO_OUT"; exit 1
}
echo "$INFO_OUT" | head -6
echo "$INFO_OUT" | grep -q 'Document type: matroska' || { echo "FAIL: mkvinfo 未解析出 matroska"; exit 1; }
echo "$INFO_OUT" | grep -q 'Track type: audio' || { echo "FAIL: mkvinfo 未解析出 audio track"; exit 1; }
echo "PASS: mkvinfo 解析生成文件"

echo "[test] cleanup"
rm -f "$OUTPUT" "$INPUT"
[ ! -e "$INPUT" ] && [ ! -e "$OUTPUT" ] && echo "PASS: 临时文件已清理"
echo "ALL INTEGRATION TESTS PASSED"
