#!/bin/sh
# scons-detect.sh — HarmonyOS PC 适配前哨：判定源码树是否由 SCons 驱动，
# 并列出决定"是否需要构造变量注入补丁"的关键信号（对应知识条目 E429/E430）。
#
# 用法:  scons-detect.sh <source-dir>
# 退出码: 0 = SCons 工程（检出 SConstruct/SConscript）
#         1 = 非 SCons 工程
#         2 = 用法错误
#
# 只读：不向源码树写入任何文件；输出为 stdout 报告。
# 路径中立：不写死任何本机路径；工具链探测优先取 $TOOLCHAIN_BIN，
# 否则取 PATH 上 clang 所在目录。适配 OHOS aarch64 内置 clang 布局。
#
# `|| true` 约定：本脚本要 `set -e`，而 grep/find 在"未命中"时返回非 0，
# 这属于正常结果（探针信号不存在），故每处均以 `|| true` 放行并就近注释原因。
set -eu
set -o pipefail

src=${1:-}
if [ -z "$src" ] || [ ! -d "$src" ]; then
    echo "usage: $0 <source-dir>" >&2
    exit 2
fi

# find 无匹配返回非 0（工程可能只有 SConscript 而没有 SConstruct）
root_hits=$(find "$src" -maxdepth 4 -name SConstruct -type f 2>/dev/null || true)
sub_count=$(find "$src" -name SConscript -type f 2>/dev/null | wc -l | tr -d ' ')

if [ -z "$root_hits" ] && [ "$sub_count" = "0" ]; then
    echo "verdict: not-an-scons-project"
    exit 1
fi

echo "verdict: scons-project"
echo "sconstruct:"
for f in $root_hits; do
    echo "  $f"
done
echo "sconscript_count: $sub_count"

# ── 信号 1：SHELL 构造变量（SCons 走 posix_spawn，不搜 PATH → 沙箱内 127）──
for f in $root_hits; do
    echo "--- signals in $f"
    # grep 未命中返回 1：该信号不存在属正常，放行
    grep -n -m 5 'SHELL' "$f" 2>/dev/null | sed 's/^/  shell: /' || true
    # ── 信号 2：编译器自检（默认指向宿主 gcc/g++ → 交叉编译必然失败）──
    # grep 未命中返回 1：无自检的工程走策略 B
    grep -n -m 5 -E 'CheckCC|CheckCXX|CheckProg|Configure\(' "$f" 2>/dev/null | sed 's/^/  probe: /' || true
    # ── 信号 3：构造变量赋值点（补丁的注入锚点）──
    # grep 未命中返回 1：没有赋值点说明环境直传即可覆盖
    grep -n -m 5 -E "\[['\"]CC['\"]\]|\[['\"]CXX['\"]\]|['\"]CC['\"] *:|['\"]CXX['\"] *:" "$f" 2>/dev/null | sed 's/^/  compiler-var: /' || true
    # ── 信号 4：pkg-config / 外部工具调用（沙箱内常 not found）──
    # grep 未命中返回 1：无外部工具依赖即无需特殊处理
    grep -n -m 5 -E 'pkg-config|pkg_config|ParseConfig' "$f" 2>/dev/null | sed 's/^/  external-tool: /' || true
done

# ── 语言预检辅助：主体语言作用域（SCons 无 CMake manifest → 统计易被子树稀释）──
echo "--- language scope hints"
for lang in java kotlin; do
    # find 无匹配返回非 0：该语言文件不存在属正常
    n=$(find "$src" -name "*.$lang" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  .$lang files: $n"
done
for sub in android ios darwin; do
    if [ -d "$src/$sub" ]; then
        echo "  subtree present (candidate for tar --exclude): $sub/"
    fi
done

# ── 工具链探测（不写死本机路径）──
echo "--- toolchain"
if [ -n "${TOOLCHAIN_BIN:-}" ]; then
    tb=$TOOLCHAIN_BIN
else
    # command -v 未命中返回非 0：缺 clang 时回退到 /usr/bin 仅用于打印默认值
    clang_path=$(command -v clang 2>/dev/null || true)
    tb=$(dirname "${clang_path:-/usr/bin/clang}")
fi
echo "  toolchain_bin: $tb"
for t in clang clang++ llvm-ar llvm-ranlib; do
    if [ -x "$tb/$t" ]; then
        echo "  ok: $tb/$t"
    else
        echo "  missing: $tb/$t"
    fi
done
echo "  shell candidates:"
for s in /system/bin/sh /usr/bin/sh /bin/sh; do
    if [ -x "$s" ]; then
        echo "    $s"
    fi
done

echo "next:"
echo "  1) 打构造变量覆盖补丁（KB E429），由配方注入 CC/CXX/AR/RANLIB/SHELL 绝对路径；"
echo "  2) 若语言预检把主体判成 java/mixed，用 tar 排除法重建作用域树后再跑 lang-preflight（KB E430）。"
exit 0
