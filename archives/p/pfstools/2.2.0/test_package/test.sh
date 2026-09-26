#!/data/service/hnp/bin/bash
# test_package/test.sh — pfstools 2.2.0 消费者测试（test_package 层）
#
# 全部命令与期望值均为鸿蒙 PC 真机实测校正版（2026-09-24，构建机 B）：
#   - `--help` 在本上游返回 rc=1 并打印 usage（不是"帮助返回 0"）；
#   - pfscat 的 -h 是 horizontal、pfssize 的尺寸选项是 --x/--y（初稿用的 --xsize 不存在）；
#   - pfsoutpfm 从 **stdin 读 PFS**、把 PFM **写到位置参数命名的文件**
#     （初稿写的是 `pfsoutpfm stream.pfs > out.pfm`，语义反了 → 产物为空）。
# R34/PF3: 逐条真实执行被测包二进制，非 print-only 空壳。
set -u

PASS=0
TOTAL=0
FAILED=0

ok()  { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); }
bad() { TOTAL=$((TOTAL+1)); FAILED=1; echo "FAIL[#${TOTAL}]: $1" >&2; }

# 与 archives/p/pfstools/commands.json 逐项一致的 38 个可执行命令
# （由真机 CLI 审计生成：40 个产物中剔除 2 个解释器缺失的脚本，见 notes.md）
CMDS="dcraw2hdrgen jpeg2hdrgen pfsabsolute pfscat pfsclamp pfscolortransform pfscut
pfsdisplayfunction pfsextractchannels pfsflip pfsgamma pfshdrcalibrate pfsin pfsindcraw
pfsinhdrgen pfsinme pfsinpfm pfsinrgbe pfsinyuv pfsout pfsoutpfm pfsoutrgbe pfsoutyuv
pfspad pfspanoramic pfsplotresponse pfsretime pfsrotate pfssize pfstag pfstmo_drago03
pfstmo_durand02 pfstmo_fattal02 pfstmo_mai11 pfstmo_mantiuk06 pfstmo_pattanaik00
pfstmo_reinhard02 pfstmo_reinhard05"

echo "[test 1/4] 38 个申报 CLI 的存在性 + 可执行性（--help 冒烟）"
# 判据（真机实测）：可用工具 --help 返回 rc=0/1 且输出 usage；
# 解释器缺失（如 #!/bin/bash 在本平台不存在）返回 rc=127。
# ⚠ 不得用输出文本里的 "No such file or directory" 作判据 —— bash 在 conan 的
#   test cwd 下会打印 getcwd 噪声（"cannot access parent directories: No such
#   file or directory"），那是环境噪声而非执行失败（2026-09-24 首轮因此误判 6 个脚本工具）。
for t in $CMDS; do
    if ! command -v "$t" >/dev/null 2>&1; then
        bad "$t not found in PATH"
        continue
    fi
    h="$(timeout 30 "$t" --help </dev/null 2>&1)"
    RC=$?
    if [ "$RC" -eq 127 ] || [ "$RC" -eq 126 ]; then
        bad "$t 不可执行 (rc=$RC，shebang 解释器缺失): $h"
    elif [ -n "$h" ]; then
        ok
    else
        bad "$t --help 无任何 usage 输出"
    fi
done
echo "    进度: ${PASS}/${TOTAL}"

WORKDIR="${TMPDIR:-$HOME/tmp}/pfstools-testpkg.$$"
mkdir -p "$WORKDIR" || { echo "FATAL: cannot create $WORKDIR" >&2; exit 1; }
cd "$WORKDIR" || { echo "FATAL: cannot cd $WORKDIR" >&2; exit 1; }

# 2x2 HDR PFM：header "Pf\n2 2\n-1.0\n"(12B) + 4 个 little-endian float32(16B)
#   像素值 0.25 / 1.0 / 0.0 / 0.0（0.25=0x3e800000, 1.0=0x3f800000）
printf 'Pf\n2 2\n-1.0\n' > in.pfm
printf '\000\000\200\076\000\000\200\077\000\000\000\000\000\000\000\000' >> in.pfm

echo "[test 2/4] PFM -> PFS -> PFM 往返像素保真（pfsinpfm | pfsoutpfm）"
if pfsinpfm in.pfm > s.pfs && [ -s s.pfs ]; then ok; else bad "pfsinpfm produced empty PFS"; fi
if pfsoutpfm rt.pfm < s.pfs && [ -s rt.pfm ]; then ok; else bad "pfsoutpfm produced empty PFM"; fi
tail -c 16 in.pfm > a.pay
tail -c 16 rt.pfm > b.pay
if cmp -s a.pay b.pay; then ok; else bad "PFM round-trip payload differs from input"; fi
echo "    进度: ${PASS}/${TOTAL}"

echo "[test 3/4] 滤波链：pfsgamma --gamma 2.2 数值正确性"
# 0.25^(1/2.2) = 0.53182... = float32 0x3f085344 -> 小端字节 44 53 08 3f
if pfsinpfm in.pfm | pfsgamma --gamma 2.2 | pfsoutpfm g.pfm && [ -s g.pfm ]; then
    GOT="$(tail -c 16 g.pfm | head -c 4 | od -An -tx1 | tr -d ' \n')"
    if [ "$GOT" = "4453083f" ]; then
        ok
    else
        bad "pfsgamma: first pixel expected 4453083f (0.5318), got ${GOT}"
    fi
else
    bad "pfsgamma chain produced no output"
fi
echo "    进度: ${PASS}/${TOTAL}"

echo "[test 4/4] 尺寸/拼接链：pfssize --x/--y 与 pfscat --vertical"
if pfsinpfm in.pfm | pfssize --x 4 --y 4 | pfsoutpfm big.pfm; then
    DIM="$(sed -n '2p' big.pfm | tr -d '\r\n')"
    if [ "$DIM" = "4 4" ]; then ok; else bad "pfssize output header size expected '4 4', got '${DIM}'"; fi
else
    bad "pfssize chain failed"
fi
if pfsinpfm in.pfm > s2.pfs && pfscat --vertical s.pfs s2.pfs | pfsoutpfm cat.pfm; then
    DIM="$(sed -n '2p' cat.pfm | tr -d '\r\n')"
    if [ "$DIM" = "2 4" ]; then ok; else bad "pfscat --vertical expected '2 4', got '${DIM}'"; fi
else
    bad "pfscat --vertical chain failed"
fi

cd /
rm -rf "$WORKDIR"

echo "ASSERT_TOTAL=${TOTAL}"
echo "ASSERT_PASS=${PASS}"
echo "ASSERT_FAIL=$((TOTAL-PASS))"
if [ "$FAILED" -eq 0 ] && [ "$PASS" -eq "$TOTAL" ]; then
    echo "OK: pfstools test_package ${PASS}/${TOTAL} 断言全部通过"
    exit 0
fi
echo "ERROR: pfstools test_package ${PASS}/${TOTAL}"
exit 1
