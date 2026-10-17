#!/data/service/hnp/bin/bash
# test_package/test.sh — pccts 1.33mr33 smoke + 端到端闭环
# 在 conanrun env 下执行（PATH 已含安装的 bin/）
#
# 分栏（对应 PR 模板「测试用例对比」）：
#   [上游冒烟]   4 个生成器工具真实可执行性（banner 版本串比对）
#   [端到端]     语法 → antlr/dlg 生成 → clang++ 编译链接 → 二进制产出
#   [鸿蒙特有]   OHOS 平台边界三项
# 注：本文件属 test_package/smoke，**不计入上游用例数**（§3.5 分栏要求）。
set -u

PASS=0
FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS + 1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

HERE="$(cd "$(dirname "$0")" && pwd)"
# 工作目录必须落在 worktree **之外**（否则会在提交面留下未跟踪文件，
# 破坏 W4 派发的「工作区干净」前置）。优先用任务 env 的 TMPDIR，退回 $HOME/tmp；
# 不用 /tmp（该设备只读，§一.1）。
BASE_TMP="${TMPDIR:-$HOME/tmp}"
case "$BASE_TMP" in /tmp|"") BASE_TMP="$HOME/tmp" ;; esac
mkdir -p "$BASE_TMP" 2>/dev/null || BASE_TMP="$HOME/tmp"
WORK="$BASE_TMP/pccts-tp-$$"
rm -rf "$WORK"; mkdir -p "$WORK"
# 退出即清理，避免残留
trap 'rm -rf "$WORK"' EXIT

echo "=== [上游冒烟] 四个生成器工具 ==="

# 注：antlr / genmk **无参时退出码为 1**（用法提示即非零），dlg / sor 为 0 ——
# 这是上游既定行为，不是失败。故 banner 判定一律只看输出内容，不看退出码。
banner_of() {   # banner_of <cmd...> -> 输出首行（不因非零退出而短路）
    "$@" 2>&1 || true
}

out="$(banner_of antlr)"
if printf '%s' "$out" | grep -q "Antlr parser generator"; then
    ok "antlr 可执行，banner: $(printf '%s' "$out" | head -1)"
else
    bad "antlr banner 异常: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
fi

out="$(banner_of dlg)"
if printf '%s' "$out" | grep -q "dlg  Version"; then
    ok "dlg 可执行，banner: $(printf '%s' "$out" | head -1)"
else
    bad "dlg banner 异常"
fi

out="$(banner_of sor)"
if printf '%s' "$out" | grep -q "Sorcerer"; then
    ok "sor 可执行，banner: $(printf '%s' "$out" | head -1)"
else
    bad "sor banner 异常"
fi

out="$(banner_of genmk)"
if printf '%s' "$out" | grep -q "genmk"; then
    ok "genmk 可执行: $(printf '%s' "$out" | head -1 | cut -c1-60)"
else
    bad "genmk banner 异常: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
fi

echo "=== [端到端] 语法 → antlr/dlg 生成 → clang++ 编译链接 ==="

# 夹具 test.g 取自上游 testcpp/1/test.g（ANTLR 1.x 语法，已实测全链通过）
cp "$HERE/test.g" "$WORK/" || { bad "夹具 test.g 缺失"; exit 1; }
cd "$WORK" || { bad "无法进入工作目录"; exit 1; }

if out="$(antlr -CC test.g 2>&1)"; then
    if [ -f parser.dlg ] && [ -f tokens.h ] && [ -f Expr.cpp ] && [ -f test.cpp ]; then
        ok "antlr 生成 4 件产物（test.cpp / Expr.cpp / parser.dlg / tokens.h）"
    else
        bad "antlr 返回 0 但产物不全: $(ls)"
    fi
else
    bad "antlr 执行失败: $(printf '%s' "$out" | tail -3)"
fi

if out="$(dlg -C2 -i -CC parser.dlg 2>&1)"; then
    if [ -f DLGLexer.cpp ] && [ -f DLGLexer.h ]; then
        ok "dlg 生成 2 件产物（DLGLexer.cpp / DLGLexer.h）"
    else
        bad "dlg 返回 0 但 DLGLexer 缺失"
    fi
else
    bad "dlg 执行失败: $(printf '%s' "$out" | tail -3)"
fi

# 从安装的 include/ 取 PCCTS 运行期头与源（package() 落盘面）。
# 不依赖 CONAN_PCCTS_ROOT（conanrun 不一定导出它，set -u 下会直接未绑定变量报错）——
# 改为按 bindirs 同级推导，并对两个候选逐一探测。
INC_DIR=""
ANTLR_BIN="$(command -v antlr || true)"
if [ -n "$ANTLR_BIN" ]; then
    PKG_ROOT="$(cd "$(dirname "$ANTLR_BIN")/.." && pwd)"
    for c in "$PKG_ROOT/include" "${CONAN_PCCTS_ROOT:-}/include"; do
        [ -n "$c" ] && [ -f "$c/AParser.h" ] && INC_DIR="$c" && break
    done
fi

if [ ! -f "$INC_DIR/AParser.h" ]; then
    bad "安装的 include/AParser.h 未找到（INC_DIR=$INC_DIR）"
else
    ok "安装头就位: $INC_DIR/AParser.h"
    if out="$(clang++ -DPCCTS_USE_NAMESPACE_STD -I. -I"$INC_DIR" \
               -o t test.cpp Expr.cpp DLGLexer.cpp \
               "$INC_DIR/AParser.cpp" "$INC_DIR/DLexerBase.cpp" "$INC_DIR/ATokenBuffer.cpp" 2>&1)"; then
        if [ -x ./t ]; then
            ok "clang++ 编译链接成功，产出可执行 t ($(wc -c < ./t) 字节)"
        else
            bad "clang++ 返回 0 但 t 未产出"
        fi
    else
        bad "clang++ 编译链接失败: $(printf '%s' "$out" | grep -E 'error:' | head -3 | tr '\n' ' ')"
    fi
fi

echo "=== [鸿蒙特有] OHOS 平台边界 ==="

# H1: OHOS 无 cc/gcc、只有 clang —— 上游 makefile 全部硬编码 CC=cc，
#     这正是本包 makefile 层必须自写 CC=clang 的根据（正/反两面记录）
if command -v clang >/dev/null 2>&1; then
    ok "OHOS clang 可用: $(clang --version 2>&1 | head -1)"
else
    bad "OHOS clang 缺失"
fi
if command -v cc >/dev/null 2>&1; then
    echo "  ⚠️  cc 存在（与本设备实测不符，请复核）"
else
    ok "OHOS 无 cc/gcc —— 佐证配方 CC=clang 的必要性（上游 makefile 硬编码 cc 必 127）"
fi

# H2: /system/bin/sh 不能 exec ELF → 必须 bash 包装驱动
if [ -n "${BASH:-}" ] || [ -n "${BASH_VERSION:-}" ]; then
    ok "由 bash 驱动生效（OHOS /system/bin/sh 不可 exec ELF，模板口径）"
else
    bad "当前非 bash 驱动"
fi

# H3: 产物 ELF 架构自证 aarch64
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    archline="$("$READELF" -h "$(command -v antlr)" 2>/dev/null | grep -E 'Machine')"
    if printf '%s' "$archline" | grep -qi "AArch64"; then
        ok "antlr ELF 架构自证 aarch64:$(printf '%s' "$archline" | tr -s ' ')"
    else
        bad "antlr ELF 架构异常: $archline"
    fi
else
    echo "  ⚠️  readelf 不可用，跳过 ELF 架构自证（未计入 PASS）"
fi

echo
echo "=== test_package 汇总: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
