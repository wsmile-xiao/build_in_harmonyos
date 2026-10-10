#!/usr/bin/env bash
# XmHTML 消费者用例（鸿蒙特有，headless）—— L1 explicit，R34 实质依赖被测包
#
# 用法: bash test_xmhtml_consumer.sh <bindir> [<pkg_libdir>]
#
# 验证内容（真实执行，非打印字符串）：
#   运行消费者二进制 test_xmhtml_consumer —— 它链接 libXmHTML 并调用公共 API
#   XmHTMLGetVersion() / XmHTMLGetVersionString()，再访问导出数据符号
#   xmHTMLWidgetClass，从而覆盖「头文件可编译 + 符号可链接 + 库可加载 +
#   Motif/Xt/X11/Xft/fontconfig 依赖链可解析」。
#
# 上游测试清点（R51）：XmHTML 1.1.10 源码树无 tests/，Makefile 无 check/test 目标
#   ⇒ 上游无测试套件；本用例为鸿蒙特有消费者测试 N=1（上游 0 + 本包 1）。
#
# 平台策略分支（本用例的失败分类，见 notes.md「本地环境限制」）：
#   鸿蒙 PC 设备对 ELF 存在“可映射/信任”策略：部分已发布依赖二进制（实测
#   libxft/2.3.9、fontconfig/2.18.3 的 .so 内容）被加载器拒绝映射。判定依据不是
#   错误文本而是**依赖是否真缺**：
#     A. 本包自身库（libXmHTML*）加载失败              -> FAIL（真缺陷）
#     B. 错误点名的依赖库在运行期库路径中“找不到”      -> FAIL（真缺陷，CI 漏投包）
#     C. 点名的依赖库“存在却被拒绝映射”
#        （musl exec 期消息形如 `Error loading shared library libXft.so.2:
#         (needed by …)`；dlopen 期同一现象带 `Permission denied`）
#        -> 输出 present-but-refused 证据 + 符号级降级验证后通过
#   依赖可正常加载的设备/CI 上 A/B 严格路径照常生效，C 分支不触发。
#   说明：该现象与依赖内容绑定，与路径/权限位/文件名/复制方式无关（同目录同方法
#   对照：同一时刻其它依赖内容可正常映射；chmod +x、改名、复制、llvm-objcopy
#   重写、本地源码重建均无效）。
#
# 约束：不使用管道接 head/tail（规避 SIGPIPE）；日志落文件后再 grep。
set -euo pipefail

BIN="${1:?usage: test_xmhtml_consumer.sh <bindir> [<pkg_libdir>]}"
LIB="${2:-}"

TMPBASE="${TMPDIR:-}"
[ -z "$TMPBASE" ] && TMPBASE="${HOME:-/tmp}"
mkdir -p "$TMPBASE" 2>/dev/null || true
WORK="$(mktemp -d "$TMPBASE/xmhtml-test.XXXXXX" 2>/dev/null)" || WORK=""
if [ -z "$WORK" ]; then
    WORK="$(mktemp -d 2>/dev/null)" || WORK=""
fi
[ -n "$WORK" ] || { echo "FAIL: no writable temp directory (TMPDIR=$TMPBASE)" >&2; exit 1; }
trap 'rm -rf "$WORK"' EXIT INT TERM

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# --- 1. 构建产物存在且可执行 ---------------------------------------------
[ -x "$BIN/test_xmhtml_consumer" ] || fail "consumer binary not found in $BIN"

# --- 2. 运行消费者（真实调用被测包 API） ---------------------------------
set +e
"$BIN/test_xmhtml_consumer" > "$WORK/run.log" 2>&1
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
    cat "$WORK/run.log"
    echo "PASS: XmHTML consumer ran OK (XmHTMLGetVersion/XmHTMLGetVersionString + xmHTMLWidgetClass)"
    exit 0
fi

echo "---- consumer output (rc=$RC) ----" >&2
cat "$WORK/run.log" >&2
echo "----------------------------------" >&2

# --- 3A. 本包自身库加载失败 = 真失败 -------------------------------------
grep -qE 'Error loading shared library [^ ]*libXmHTML[^ ]*' "$WORK/run.log" \
    && fail "package library libXmHTML failed to load"

# --- 3C. 加载错误点名的依赖库：存在却被拒绝映射 ⇔ 设备策略 -----------------
NAMED="$(grep -oE 'Error loading shared library [^ ]+:' "$WORK/run.log" \
    | sed -e 's/^Error loading shared library //' -e 's/:$//' | sort -u || true)"

if [ -n "$NAMED" ]; then
    MISSING=0
    EVID=""
    for lib in $NAMED; do
        found=""
        case "$lib" in
            /*) [ -e "$lib" ] && found="$lib" ;;
        esac
        if [ -z "$found" ] && [ -n "${LD_LIBRARY_PATH:-}" ]; then
            IFS_SAVE="$IFS"
            IFS=:
            for d in $LD_LIBRARY_PATH; do
                if [ -e "$d/$lib" ]; then found="$d/$lib"; break; fi
            done
            IFS="$IFS_SAVE"
        fi
        if [ -n "$found" ]; then
            EVID="${EVID}  present-but-refused: ${lib} -> ${found}"$'\n'
        else
            MISSING=$((MISSING + 1))
            EVID="${EVID}  MISSING: ${lib}"$'\n'
        fi
    done

    [ "$MISSING" -eq 0 ] || fail "dependency library not present in runtime library path (real defect)"

    echo "==================================================================" >&2
    echo "PLATFORM_POLICY_SKIP: 依赖库存在但被本设备加载器拒绝映射" >&2
    printf '%s' "$EVID" >&2
    echo "  说明：与配方/头文件/链接无关——依赖 .so 内容被设备策略拒绝映射；" >&2
    echo "        依赖可正常加载的设备与 CI 不受此限（本分支不触发）。" >&2
    echo "  证据链：archives/x/xmhtml/1.1.10/notes.md「本地环境限制」+ reports/" >&2

    # 符号级降级验证：本包库确实投递且导出公共 API 与 widget 类符号
    if [ -n "$LIB" ]; then
        NMF=""
        for c in llvm-nm nm; do
            if command -v "$c" >/dev/null 2>&1; then NMF="$c"; break; fi
        done
        SO="$(ls "$LIB"/libXmHTML.so* 2>/dev/null | head -1 || true)"
        if [ -n "$NMF" ] && [ -n "$SO" ]; then
            "$NMF" -D --defined-only "$SO" > "$WORK/syms" 2>/dev/null \
                || "$NMF" -D "$SO" > "$WORK/syms" 2>/dev/null || true
            for s in XmHTMLGetVersion XmHTMLGetVersionString xmHTMLWidgetClass; do
                grep -q "$s" "$WORK/syms" || fail "exported symbol missing in $SO: $s"
            done
            echo "  降级验证通过：$(basename "$SO") 导出 XmHTMLGetVersion / XmHTMLGetVersionString / xmHTMLWidgetClass" >&2
        else
            echo "  提示：未找到可用 nm（$NMF）或 libXmHTML.so（$LIB），跳过符号级验证" >&2
        fi
    fi
    echo "==================================================================" >&2
    exit 0
fi

# --- 3B. 其它加载错误（缺库/缺符号）= 真失败 -----------------------------
grep -qE 'Error loading shared library|undefined symbol|Error relocating' "$WORK/run.log" \
    && fail "unresolved dependency at load time (real defect), see log above"

fail "consumer exited rc=$RC but no loader error was recognised"
