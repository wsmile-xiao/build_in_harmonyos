#!/bin/sh
# test_package/test.sh — 消费者用例（以真实消费者方式驱动已安装的 skia）
#
# 验证 CPU 光栅化核心面在 OHOS 上可用：光栅 surface / 立即模式绘制（矩形+路径描边+抗锯齿）/
# 像素回读 / libpng 编码（SkPngEncoder）/ 解码（SkCodec）。
set -u

BIN="./consumer"
fails=0
checks=0
c() { checks=$((checks + 1)); if eval "$2"; then echo "PASS $checks: $1"; else echo "FAIL $checks: $1"; fails=$((fails + 1)); fi; }

echo "--- skia 2.88.9 consumer checks ---"

OUT="$("$BIN" 2>&1)"
rc=$?
echo "$OUT"

c "C1 consumer exits 0" "[ $rc -eq 0 ]"
c "C2 raster surface created" "echo \"\$OUT\" | grep -q 'PASS: SkSurface::MakeRasterN32Premul'"
c "C3 immediate-mode raster draw (rect+path)" "echo \"\$OUT\" | grep -q 'PASS: CPU raster'"
c "C4 pixel readback" "echo \"\$OUT\" | grep -q 'PASS: surface->readPixels'"
c "C5 center pixel is opaque red" "echo \"\$OUT\" | grep -q 'PASS: center pixel is opaque red'"
c "C6 libpng encode path" "echo \"\$OUT\" | grep -q 'PASS: SkPngEncoder::Encode'"
c "C7 PNG signature" "echo \"\$OUT\" | grep -q 'PASS: PNG signature'"
c "C8 libpng decode path (SkCodec)" "echo \"\$OUT\" | grep -q 'PASS: SkCodec::MakeFromData'"
c "C9 decoded image size matches" "echo \"\$OUT\" | grep -q 'PASS: decoded image size'"
c "C10 no failing assertions" "! echo \"\$OUT\" | grep -q '^FAIL:'"

echo "test.sh skia 2.88.9: $((checks - fails))/$checks checks PASS"
[ "$fails" -eq 0 ] || exit 1
exit 0
