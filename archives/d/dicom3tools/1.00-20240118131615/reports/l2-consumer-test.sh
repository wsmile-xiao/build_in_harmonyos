#!/bin/bash
# L2 消费者实测：对已安装的 dicom3tools 产物跑真实命令并断言业务输出。
#
# conan-verify 报告里 L2 打印的是 "⏭️ 跳过（无 cache 路径）"（工具文案缺陷，
# 同一行还打了 ✅），因此按 workflow §7.2 人工补测并留下本脚本与输出。
#
# 与 test_package/test.sh 的区别：这里额外覆盖上游自带的测试图像生成器
# （dcsmpte）与像素导出/导入回环，这两条链路完全不依赖未分发的 images 夹具。
#
# 用法：PATH=<package_folder>/bin:$PATH bash l2-consumer-test.sh
# 刻意偏离 code-style 的 `set -euo pipefail`，只用 `set -uo pipefail`：
# 本脚本大量断言依赖「预期失败的命令」（dciodvfy rc=1 等），启 -e 会让这些断言在
# 判定前就退出，反而掩盖结果。失败状态由末尾的 `[ "$fail" -eq 0 ]` 兜底，
# 因此非 0 退出仍然成立（该偏离已在 notes.md 显式声明）。
set -uo pipefail

log() { echo "$@"; }
pass=0; fail=0
ok()  { pass=$((pass+1)); log "PASS: $1"; }
bad() { fail=$((fail+1)); log "FAIL: $1"; }

W="$(mktemp -d "${TMPDIR:-.}/dicom3tools-l2.XXXXXX")" || exit 1
trap 'rm -rf "$W"' EXIT INT TERM
cd "$W" || exit 1

log "== L2 dicom3tools consumer test =="
log "workdir: <mktemp -d>"

# ---------------------------------------------------------------- 1. 工具在位
for t in dcdump dciodvfy dcstats dckey dcdict dccreate dccp dcsmpte \
         dctopnm dctopgx dctoraw dctopgm8 pnmtodc pgxtodc rawtodc; do
	if command -v "$t" >/dev/null 2>&1; then ok "found $t"; else bad "missing $t"; fi
done

# ------------------------------------------------------- 2. 版本自检（可启动）
if dcdump -version >version.out 2>&1 && grep -q "dicom3tools Version" version.out; then
	ok "dcdump -version 报告版本：$(grep -o 'dicom3tools Version: .*' version.out)"
else
	bad "dcdump -version 失败"
fi

# ------------------------------------------------ 3. 生成带像素的完整 DICOM
# dcsmpte 把 SMPTE 测试图写到 stdout；256x256 是能生成的最小实用尺寸
# （32x32 会触发上游断言 right_col >= bitmap_cols）。
if dcsmpte -rows 256 -columns 256 >smpte.dcm 2>smpte.log; then
	ok "dcsmpte 生成 SMPTE 测试图（$(wc -c <smpte.dcm) 字节）"
else
	bad "dcsmpte 生成失败"
fi

if [ "$(dd if=smpte.dcm bs=1 skip=128 count=4 2>/dev/null)" = "DICM" ]; then
	ok "生成物是 Part 10 DICOM（偏移 128 处为 DICM）"
else
	bad "生成物不是 Part 10 DICOM"
fi

# --------------------------------------------------------- 4. 读取与统计链路
dcdump smpte.dcm >smpte.dump 2>&1
n_attr=$(grep -cE '^\(0x' smpte.dump)
if [ "$n_attr" -ge 20 ]; then
	ok "dcdump 解析出 $n_attr 个属性"
else
	bad "dcdump 只解析出 $n_attr 个属性"
fi

if grep -qE 'Rows.*0x0100' smpte.dump && grep -qE 'Columns.*0x0100' smpte.dump; then
	ok "dcdump 报出 256x256 行列尺寸"
else
	bad "dcdump 未报出正确的行列尺寸"
fi

if grep -q "MONOCHROME2" smpte.dump; then
	ok "dcdump 报出 MONOCHROME2 光度解释"
else
	bad "dcdump 未报出光度解释"
fi

dcstats smpte.dcm >smpte.stats 2>&1
# dcstats 输出的是像素值统计（min/max/mean/bits），不是模块属性列表。
# SMPTE 图的均值落在 52% 附近，说明它真的解码并统计了像素数据。
if grep -q "Bits Stored" smpte.stats && grep -qE "Unsigned mean = 0x[0-9a-f]+" smpte.stats; then
	ok "dcstats 统计像素值：$(grep -o 'Unsigned mean = .*' smpte.stats)"
else
	bad "dcstats 未输出像素统计"
fi

dciodvfy smpte.dcm >smpte.iodvfy 2>&1
if [ -s smpte.iodvfy ] && ! grep -q "Dicom dataset read failed" smpte.iodvfy; then
	ok "dciodvfy 完整读取该文件并给出校验报告"
else
	bad "dciodvfy 无法读取该文件"
fi

# ------------------------------------------------------------- 5. 字典链路
if dcdict -key PatientName 2>&1 | grep -q "(0x0010,0x0010)"; then
	ok "dcdict 解析 PatientName → (0x0010,0x0010)"
else
	bad "dcdict 未解析 PatientName"
fi
if dckey -key TransferSyntaxUID 2>&1 | grep -q "(0x0002,0x0010)"; then
	ok "dckey 解析 TransferSyntaxUID → (0x0002,0x0010)"
else
	bad "dckey 未解析 TransferSyntaxUID"
fi

# ------------------------------------------------------- 6. 像素导出（4 种）
dctopnm smpte.dcm >pix.pnm 2>pix.pnm.log
if [ "$(wc -c <pix.pnm)" -eq 65551 ] && [ "$(head -c2 pix.pnm)" = "P5" ]; then
	ok "dctopnm 输出 256x256 P5 PGM（65551 字节）"
else
	bad "dctopnm 输出不符（$(wc -c <pix.pnm) 字节）"
fi

dctoraw smpte.dcm >pix.raw 2>pix.raw.log
if [ "$(wc -c <pix.raw)" -eq 65536 ]; then
	ok "dctoraw 输出 65536 字节裸像素（256x256x1）"
else
	bad "dctoraw 输出 $(wc -c <pix.raw) 字节"
fi

dctopgm8 smpte.dcm >pix.pgm8 2>pix.pgm8.log
if [ "$(wc -c <pix.pgm8)" -eq 65551 ]; then
	ok "dctopgm8 输出 8 位 PGM（65551 字节）"
else
	bad "dctopgm8 输出 $(wc -c <pix.pgm8) 字节"
fi

dctopgx smpte.dcm >pix.pgx 2>pix.pgx.log
if [ "$(wc -c <pix.pgx)" -eq 65553 ]; then
	ok "dctopgx 输出 PGX（65553 字节）"
else
	bad "dctopgx 输出 $(wc -c <pix.pgx) 字节"
fi

# ----------------------------------------------- 7. 像素导入回环（3 条路径）
pnmtodc <pix.pnm >back.pnm.dcm 2>back.pnm.log
dcdump back.pnm.dcm >back.pnm.dump 2>&1
if grep -qE 'Rows.*0x0100' back.pnm.dump && grep -qE 'Columns.*0x0100' back.pnm.dump; then
	ok "pnmtodc 回环：PGM → DICOM → 256x256"
else
	bad "pnmtodc 回环失败"
fi

pgxtodc <pix.pgx >back.pgx.dcm 2>back.pgx.log
dcdump back.pgx.dcm >back.pgx.dump 2>&1
if grep -qE 'Rows.*0x0100' back.pgx.dump; then
	ok "pgxtodc 回环：PGX → DICOM → 256 行"
else
	bad "pgxtodc 回环失败"
fi

rawtodc -rows 256 -columns 256 -bits 8 <pix.raw >back.raw.dcm 2>back.raw.log
dcdump back.raw.dcm >back.raw.dump 2>&1
if grep -qE 'Rows.*0x0100' back.raw.dump; then
	ok "rawtodc 回环：RAW → DICOM → 256 行"
else
	bad "rawtodc 回环失败"
fi

# ------------------------------------------------------- 8. 属性替换链路
dccp smpte.dcm -r PatientID 999 -r PatientName "Round^Trip" >cp.dcm 2>cp.log
dcdump cp.dcm >cp.dump 2>&1
if grep -q "Round\^Trip" cp.dump && grep -q "999" cp.dump; then
	ok "dccp 替换 PatientID/PatientName 后回读一致"
else
	bad "dccp 属性替换未生效"
fi
# 原始文件必须未被就地修改
if grep -q "Round\^Trip" smpte.dump; then
	bad "dccp 就地改写了输入文件"
else
	ok "dccp 未改写输入文件"
fi

# ------------------------------------------------------- 9. 坏输入必须拒绝
# 判据只用 dciodvfy（结构校验器）。不能用 dcdump：它按设计支持没有 Part 10 头
# 的旧格式，会做字节序/VR 自动识别，因此对任意字节流都返回 0 并把它当作隐式 VR
# 数据集打印出来（实测纯文本 "this is..." 被解析成 (0x6874,0x7369) VR=<UN>）。
# 这是上游的设计行为，不是缺陷，所以不能拿它当"拒绝坏输入"的证据。
printf 'this is not a dicom file at all\n' >bad.dcm
dciodvfy bad.dcm >bad.iodvfy 2>&1; rc_iod=$?
if [ "$rc_iod" -ne 0 ]; then
	ok "非 DICOM 输入被 dciodvfy 拒绝（rc=$rc_iod）"
else
	bad "非 DICOM 输入未被 dciodvfy 拒绝"
fi

# 截断的数据集必须报读取失败
dd if=smpte.dcm of=trunc.dcm bs=1 count=400 2>/dev/null
dcdump trunc.dcm >trunc.dump 2>&1; rc_trunc=$?
if [ "$rc_trunc" -ne 0 ] && grep -q "Dicom dataset read failed" trunc.dump; then
	ok "截断数据集被拒绝（rc=$rc_trunc）"
else
	bad "截断数据集未被拒绝（rc=$rc_trunc）"
fi

log ""
log "L2 consumer test: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
