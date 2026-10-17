#!/usr/bin/env bash
# test.sh — pdftoipe 7.2.29.2 消费者 + 平台验证
#
# 用法: test.sh <pdftoipe 可执行文件绝对路径>
#
# 分三组断言：
#   A 消费者用例   上游 CLI 契约 + PDF→Ipe XML 端到端转换（图形与文字保真）
#   B 鸿蒙特有测试 OHOS musl libc / aarch64 LP64 小端数据模型
#   C PC 特有测试  HarmonyOS PC ELF 代码签名（.codesign 段）与产物形态
#
# 输入 PDF 由本脚本现场合成（纯 ASCII、xref 偏移固定、无尾随空格），不引入二进制夹具；
# 中间文件与输出全部落在临时目录，不在工作区留残留。
set -euo pipefail

BIN="${1:-}"
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "[fail] 用法: $0 <pdftoipe 可执行文件绝对路径>（当前: '${BIN}'）"
    exit 2
fi

PASS=0
FAIL=0
A_PASS=0
A_FAIL=0

ok()  { PASS=$((PASS + 1)); printf '  [ok]   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  [fail] %s\n' "$1"; }

# OHOS 上 /data/service/hnp/bin/readelf 为 LLVM 实现，输出与 GNU readelf 兼容
READELF=""
for cand in readelf llvm-readelf /data/service/hnp/bin/readelf; do
    if command -v "$cand" >/dev/null 2>&1; then
        READELF="$cand"
        break
    fi
done

WORK="$(mktemp -d "${TMPDIR:-$HOME}/pdftoipe-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

echo "[step] pdftoipe 消费者测试"
echo "        binary : $BIN"
echo "        workdir: $WORK"

# ── 现场合成测试用 PDF ────────────────────────────────────────────────────────
# 单页 200x200：红色斜线描边（线宽 1）+ 绿色矩形填充 + 24pt 蓝字 "Hi"
cat > minimal.pdf <<'PDFEOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 104 >>
stream
1 w
1 0 0 RG
10 10 m
190 190 l
S
0 1 0 rg
50 50 100 100 re
f
0 0 1 rg
BT /F1 24 Tf 40 120 Td (Hi) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000241 00000 n
0000000395 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
492
%%EOF
PDFEOF

# HMDFS 写读延迟：确认夹具落盘完整再继续，避免读到半截文件造成假红
for _ in 1 2 3 4 5; do
    if [ -s minimal.pdf ] && grep -qF '%%EOF' minimal.pdf; then
        break
    fi
    sleep 1
done
if [ ! -s minimal.pdf ] || ! grep -qF '%%EOF' minimal.pdf; then
    echo "[fail] 测试夹具 minimal.pdf 生成失败"
    exit 2
fi

# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[step] A. 消费者用例（上游 CLI 契约 + PDF→Ipe XML 端到端）"
# ══════════════════════════════════════════════════════════════════════════════

# A1: -h 帮助输出（上游行为：usage 走 stderr，退出码 1）
if "$BIN" -h > help.out 2>&1; then rc=0; else rc=$?; fi
a1=1
[ "$rc" -eq 1 ] || a1=0
grep -qF 'pdftoipe version 2024/11/15' help.out || a1=0
grep -qF 'Usage: pdftoipe [options] <PDF-file> [<XML-file>]' help.out || a1=0
if [ "$a1" -eq 1 ]; then
    ok "A1 -h 打印版本与用法，退出码 1"
else
    bad "A1 -h 帮助契约不符（rc=$rc）"
fi

# A2: 缺少输入参数必须失败
if "$BIN" > /dev/null 2>&1; then rc=0; else rc=$?; fi
if [ "$rc" -eq 1 ]; then
    ok "A2 无参数调用退出码 1"
else
    bad "A2 无参数调用未返回 1（rc=$rc）"
fi

# A3: 端到端转换 + 默认输出名（minimal.pdf → minimal.ipe）
if "$BIN" minimal.pdf > conv.log 2>&1; then rc=0; else rc=$?; fi
if [ "$rc" -eq 0 ] && [ -s minimal.ipe ]; then
    ok "A3 转换为默认输出 minimal.ipe，退出码 0"
else
    bad "A3 转换失败（rc=$rc，输出缺失或为空）"
fi

# A4: Ipe XML 骨架
a4=0
if [ -s minimal.ipe ]; then
    a4=1
    grep -qF '<?xml version="1.0"?>' minimal.ipe || a4=0
    grep -qF '<ipe version="70000" creator="pdftoipe 2024/11/15">' minimal.ipe || a4=0
    grep -qF '<page>' minimal.ipe || a4=0
fi
if [ "$a4" -eq 1 ]; then
    ok "A4 输出为 Ipe 7 XML（版本头 + page 元素）"
else
    bad "A4 Ipe XML 骨架不符"
fi

# A5: 图形保真 —— 描边颜色/线宽/坐标 + 填充颜色/矩形顶点
a5=0
if [ -s minimal.ipe ]; then
    a5=1
    grep -qF 'stroke="1.000000 0.000000 0.000000" pen="1"' minimal.ipe || a5=0
    grep -qF 'fill="0.000000 1.000000 0.000000"' minimal.ipe || a5=0
    grep -qE '^10 10 m$' minimal.ipe || a5=0
    grep -qE '^190 190 l$' minimal.ipe || a5=0
    grep -qE '^50 50 m$' minimal.ipe || a5=0
    grep -qE '^150 150 l$' minimal.ipe || a5=0
fi
if [ "$a5" -eq 1 ]; then
    ok "A5 图形保真（描边色 RGB/线宽/坐标 + 填充色 + 矩形顶点）"
else
    bad "A5 图形保真断言失败"
fi

# A6: 文字保真（字号 + 变换矩阵 + 文本内容）与 -notext 选项
a6=0
if [ -s minimal.ipe ] \
    && grep -qF 'size="24"' minimal.ipe \
    && grep -qF 'matrix="1 0 0 1 40 120"' minimal.ipe \
    && grep -qF '>Hi</text>' minimal.ipe; then
    a6=1
fi
if "$BIN" -notext minimal.pdf notext.ipe > /dev/null 2>&1; then rc=0; else rc=$?; fi
a6_nt=0
if [ "$rc" -eq 0 ] && [ -s notext.ipe ] && ! grep -qF '<text' notext.ipe; then
    a6_nt=1
fi
if [ "$a6" -eq 1 ] && [ "$a6_nt" -eq 1 ]; then
    ok "A6 文字保真（字号/矩阵/内容）与 -notext 丢弃文字"
else
    bad "A6 文字保真或 -notext 选项断言失败"
fi

# A7: 包 bin/ 必须经 VirtualRunEnv 导出到消费者 PATH（消费者无需记绝对路径）
if command -v pdftoipe >/dev/null 2>&1 && [ -x "$(command -v pdftoipe)" ]; then
    ok "A7 包 bin/ 已导出到消费者 PATH（command -v pdftoipe -> $(command -v pdftoipe)）"
else
    bad "A7 包 bin/ 未导出到消费者 PATH（cpp_info.bindirs 或 VirtualRunEnv 失效）"
fi

A_PASS="$PASS"
A_FAIL="$FAIL"

# ── 预生成 ELF 元数据（B/C 两组共用）─────────────────────────────────────────
ELF_OK=0
if [ -n "$READELF" ] \
    && "$READELF" -h "$BIN" > hdr.txt 2>&1 \
    && "$READELF" -d "$BIN" > dyn.txt 2>&1 \
    && "$READELF" -S "$BIN" > sec.txt 2>&1; then
    ELF_OK=1
fi

# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[step] B. 鸿蒙特有测试（musl libc / aarch64 LP64 小端）"
# ══════════════════════════════════════════════════════════════════════════════

if [ "$ELF_OK" -eq 0 ]; then
    bad "B1 无法读取 ELF 元数据（readelf 缺失或执行失败）"
    bad "B2 无法读取 ELF 元数据（readelf 缺失或执行失败）"
else
    # B1: OHOS/musl —— 动态依赖 libc.so；不得出现 glibc 的 libc.so.6；
    #     C++ 运行时必须是 OHOS 的 libc++_shared.so（非 libstdc++）
    b1=1
    grep -qF 'Shared library: [libc.so]' dyn.txt || b1=0
    if grep -qF 'libc.so.6' dyn.txt; then
        b1=0
    fi
    grep -qF 'Shared library: [libc++_shared.so]' dyn.txt || b1=0
    if [ "$b1" -eq 1 ]; then
        ok "B1 鸿蒙 libc 事实：link libc.so + libc++_shared.so，无 glibc libc.so.6"
    else
        bad "B1 鸿蒙 libc 事实断言失败"
    fi

    # B2: aarch64 LP64 小端数据模型
    b2=1
    grep -qF 'ELF64' hdr.txt || b2=0
    grep -qF "2's complement, little endian" hdr.txt || b2=0
    grep -qF 'AArch64' hdr.txt || b2=0
    if [ "$b2" -eq 1 ]; then
        ok "B2 目标数据模型：ELF64 / little endian / AArch64"
    else
        bad "B2 目标数据模型断言失败"
    fi
fi

B_PASS=$((PASS - A_PASS))
B_FAIL=$((FAIL - A_FAIL))

# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[step] C. PC 特有测试（HarmonyOS PC ELF 代码签名 / 产物形态）"
# ══════════════════════════════════════════════════════════════════════════════

if [ "$ELF_OK" -eq 0 ]; then
    bad "C1 无法读取 ELF 节表（readelf 缺失或执行失败）"
    bad "C2 无法读取 ELF 文件头（readelf 缺失或执行失败）"
else
    # C1: 鸿蒙 PC 要求加载期校验 ELF .codesign 段；缺失则运行期 Permission denied
    if grep -qF '.codesign' sec.txt; then
        ok "C1 产物含鸿蒙代码签名段 .codesign"
    else
        bad "C1 产物缺失 .codesign 签名段（鸿蒙 PC 无法加载）"
    fi

    # C2: 产物形态 = 位置无关可执行文件（DYN/PIE）+ 具备可执行权限
    c2=1
    grep -qE 'DYN \(Position-Independent Executable file\)' hdr.txt || c2=0
    [ -x "$BIN" ] || c2=0
    if [ "$c2" -eq 1 ]; then
        ok "C2 产物为 PIE 动态可执行文件且带可执行权限"
    else
        bad "C2 产物形态断言失败"
    fi
fi

C_PASS=$((PASS - A_PASS - B_PASS))
C_FAIL=$((FAIL - A_FAIL - B_FAIL))

# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[step] 汇总"
echo "        消费者用例 (A) : ${A_PASS}/$((A_PASS + A_FAIL))"
echo "        鸿蒙特有 (B)   : ${B_PASS}/$((B_PASS + B_FAIL))"
echo "        PC 特有 (C)    : ${C_PASS}/$((C_PASS + C_FAIL))"
echo "        合计           : ${PASS}/$((PASS + FAIL))"
echo "PDFTOIPE_TEST_PACKAGE_RESULT=consumer=${A_PASS}/$((A_PASS + A_FAIL)) ohos=${B_PASS}/$((B_PASS + B_FAIL)) pc=${C_PASS}/$((C_PASS + C_FAIL)) total=${PASS}/$((PASS + FAIL))"

if [ "$FAIL" -eq 0 ]; then
    echo "[ok] ALL TESTS PASSED"
    exit 0
fi
echo "[fail] SOME TESTS FAILED"
exit 1
