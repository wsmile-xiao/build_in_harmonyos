#!/bin/sh
# boot 1.3-32 本地 R 实测编排脚本（POSIX sh，OHOS aarch64）
# ============================================================================
# 用途：把 boot 源码装入临时库，然后依次运行 R/ 下 3 个测试脚本：
#   [1/3] run_upstream_examples.R  上游 man/*.Rd 全部示例
#   [2/3] run_upstream_tests.R     上游 parallel-censboot.R + 50 个数据校验
#   [3/3] test_boot_api.R          鸿蒙适配补全的 API 测试套件
# 最后打印四行 marker 并透传非零退出码。
#
# 用法: run_local_verification.sh [boot_src_dir] [已装好的库目录]
#   参数 1: boot 源码树（含 DESCRIPTION/man/tests/data）；缺省 $BOOT_SRC 或
#           $HOME/tmp/bootsrc/boot。
#   参数 2: 已装好的 R 库目录（含 boot）；缺省 $BOOT_LIB 或 <WORK>/r-libs。
#
# 环境变量：
#   R_RUNTIME       R 运行时根（含 bin/Rscript、lib/R），缺省 $HOME/tmp/r-runtime
#   BOOT_WORK       工作/日志目录，缺省 $HOME/tmp/boot-work
#   BOOT_DEP_CACHE  依赖 tarball 缓存；BOOT_DEP_DL 可指向本地预置 tarball 目录
#   BOOT_SKIP_NET=1 跳过联网下载依赖
#   TMPDIR          临时目录（鸿蒙 /tmp 只读，务必指向可写目录）
# ============================================================================
set -u

SRC="${1:-${BOOT_SRC:-$HOME/tmp/bootsrc/boot}}"
LIB_ARG=""
[ "$#" -ge 2 ] && LIB_ARG="$2"
R_RUNTIME="${R_RUNTIME:-$HOME/tmp/r-runtime}"
WORK="${BOOT_WORK:-$HOME/tmp/boot-work}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
LIB="${BOOT_LIB:-${LIB_ARG:-$WORK/r-libs}}"

mkdir -p "$WORK" "$LIB"
# 鸿蒙 /tmp 只读 → 强制落到可写临时目录
export TMPDIR="${TMPDIR:-$WORK/tmp}"
mkdir -p "$TMPDIR"

# ---- R 运行时环境 ----
export R_HOME="$R_RUNTIME/lib/R"
export LD_LIBRARY_PATH="$R_RUNTIME/lib:$R_HOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# OHOS R 运行时以「局部可见」方式加载 LAPACK，导致依赖 LAPACK 的扩展包
# （如 Matrix/survival）在 dlopen 时报 "symbol not found: dgebal_"。
# 预加载 openblas 使其符号全局可见（仅当该库存在时）。
if [ -f "$R_HOME/lib/libopenblas.so" ]; then
    export LD_PRELOAD="$R_HOME/lib/libopenblas.so${LD_PRELOAD:+:$LD_PRELOAD}"
fi
export R_LIBS="$LIB"
RSCRIPT="$R_RUNTIME/bin/Rscript"
RBIN="$R_RUNTIME/bin/R"
if [ ! -x "$RSCRIPT" ]; then
    echo "FATAL: 找不到 Rscript: $RSCRIPT（设置 R_RUNTIME）" >&2; exit 3
fi
echo "== R 运行时版本 =="
"$RSCRIPT" --version || { echo "FATAL: Rscript 无法执行" >&2; exit 3; }

# ---- 编译器（依赖编译用；R33：显式路径，不用裸 shell 变量）----
export CC="${CC:-/data/service/hnp/bin/clang}"
export CXX="${CXX:-/data/service/hnp/bin/clang++}"
export AR="${AR:-/data/service/hnp/bin/llvm-ar}"
export RANLIB="${RANLIB:-/data/service/hnp/bin/llvm-ranlib}"

# ---- 1. 安装 boot（若库中已有则跳过）----
if [ -d "$LIB/boot" ]; then
    echo "== boot 已存在于 $LIB，跳过安装 =="
else
    echo "== R CMD INSTALL boot -> $LIB =="
    if ! "$RBIN" CMD INSTALL --library="$LIB" "$SRC"; then
        echo "FATAL: boot 安装失败" >&2; exit 4
    fi
fi

# ---- 2. 依赖预热（best-effort；失败不致命，run_upstream_tests.R 会再如实报）----
export BOOT_DEP_CACHE="${BOOT_DEP_CACHE:-$WORK/boot-dep-cache}"
mkdir -p "$BOOT_DEP_CACHE"
MIRROR="${BOOT_CRAN_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/CRAN/src/contrib}"
if [ -n "${BOOT_DEP_DL:-}" ] && [ -d "$BOOT_DEP_DL" ]; then
    cp -n "$BOOT_DEP_DL"/*.tar.gz "$BOOT_DEP_CACHE"/ 2>/dev/null || true
fi
# 若 4 个依赖都已可加载则无需任何下载
all_present=1
for pkg in lattice Matrix survival MASS; do
    "$RSCRIPT" -e "quit(save='no', status=if (requireNamespace('$pkg', quietly=TRUE)) 0L else 1L)" 2>/dev/null || all_present=0
done
need_dl=0
for pkg in lattice Matrix survival MASS; do
    ls "$BOOT_DEP_CACHE"/${pkg}_*.tar.gz >/dev/null 2>&1 || need_dl=1
done
if [ "$all_present" -eq 0 ] && [ "$need_dl" -eq 1 ] && [ "${BOOT_SKIP_NET:-0}" != 1 ] && command -v curl >/dev/null 2>&1; then
    [ -f "$BOOT_DEP_CACHE/PACKAGES" ] || \
        curl -fsSL -o "$BOOT_DEP_CACHE/PACKAGES" "$MIRROR/PACKAGES" 2>/dev/null || true
    for pkg in lattice Matrix survival MASS; do
        if ! ls "$BOOT_DEP_CACHE"/${pkg}_*.tar.gz >/dev/null 2>&1; then
            ver=$(awk -v p="$pkg" '$1=="Package:"{c=($2==p)} c&&$1=="Version:"{print $2; exit}' \
                  "$BOOT_DEP_CACHE/PACKAGES" 2>/dev/null)
            if [ -n "$ver" ]; then
                curl -fsSL -o "$BOOT_DEP_CACHE/${pkg}_${ver}.tar.gz" \
                     "$MIRROR/${pkg}_${ver}.tar.gz" 2>/dev/null || true
            fi
        fi
    done
fi
for pkg in lattice Matrix survival MASS; do
    if "$RSCRIPT" -e "quit(save='no', status=if (requireNamespace('$pkg', quietly=TRUE)) 0L else 1L)" 2>/dev/null; then
        echo "  依赖 $pkg 已可用，跳过"; continue
    fi
    tb=$(ls "$BOOT_DEP_CACHE"/${pkg}_*.tar.gz 2>/dev/null | head -n 1)
    if [ -z "$tb" ]; then
        echo "  依赖 $pkg 无 tarball，跳过（run_upstream_tests.R 将如实标注）"; continue
    fi
    echo "== 安装依赖 $pkg ($(basename "$tb")) =="
    if "$RBIN" CMD INSTALL --library="$LIB" "$tb" > "$BOOT_DEP_CACHE/install-$pkg.log" 2>&1; then
        echo "  $pkg OK"
    else
        echo "  $pkg 安装失败（见 $BOOT_DEP_CACHE/install-$pkg.log）"
    fi
done

# ---- 3. 依次运行 3 个脚本（输出同时落日志，便于提取 marker）----
echo; echo "###### [1/3] 上游示例 run_upstream_examples.R ######"
"$RSCRIPT" "$SCRIPT_DIR/run_upstream_examples.R" "$SRC" > "$WORK/examples.log" 2>&1
ex_rc=$?; cat "$WORK/examples.log"

echo; echo "###### [2/3] 上游测试 run_upstream_tests.R ######"
"$RSCRIPT" "$SCRIPT_DIR/run_upstream_tests.R" "$SRC" > "$WORK/upstream_tests.log" 2>&1
ts_rc=$?; cat "$WORK/upstream_tests.log"

echo; echo "###### [3/3] API 测试 test_boot_api.R ######"
"$RSCRIPT" "$SCRIPT_DIR/test_boot_api.R" > "$WORK/api_tests.log" 2>&1
api_rc=$?; cat "$WORK/api_tests.log"

# ---- 4. 汇总 marker ----
ex_line=$(grep -E '^EXAMPLES total=' "$WORK/examples.log" | tail -n 1)
ex_total=$(echo "$ex_line" | sed -n 's/.*total=\([0-9]*\).*/\1/p')
ex_pass=$(echo "$ex_line"  | sed -n 's/.*passed=\([0-9]*\).*/\1/p')
[ -z "$ex_total" ] && ex_total=0
[ -z "$ex_pass" ]  && ex_pass=0
if [ "$ex_rc" -eq 0 ] && [ "$ex_pass" = "$ex_total" ]; then
    EX_RESULT=PASS
else
    EX_RESULT=FAIL
fi

ts_marker=$(grep -E '^UPSTREAM_TESTS_RESULT=' "$WORK/upstream_tests.log" | tail -n 1 | sed 's/^UPSTREAM_TESTS_RESULT=//')
TS_RESULT="${ts_marker:-FAIL}"

api_line=$(grep -E '^assertions=' "$WORK/api_tests.log" | tail -n 1)
api_total=$(echo "$api_line" | sed -n 's/^assertions=\([0-9]*\).*/\1/p')
api_fail=$(echo "$api_line"  | sed -n 's/.*failures=\([0-9]*\).*/\1/p')
[ -z "$api_total" ] && api_total=0
[ -z "$api_fail" ]  && api_fail=0
api_pass=$((api_total - api_fail))
if [ "$api_rc" -eq 0 ] && [ "$api_fail" -eq 0 ] && [ "$api_total" -gt 0 ]; then
    API_RESULT=PASS
else
    API_RESULT=FAIL
fi

# TOTAL_PASS_RATE：examples 与 api 的通过条目 + upstream tests（单点，SKIPPED 不计入分母）
ts_pass=0; ts_total=0
case "$TS_RESULT" in
    PASS) ts_pass=1; ts_total=1 ;;
    FAIL) ts_pass=0; ts_total=1 ;;
    *)    ts_pass=0; ts_total=0 ;;   # SKIPPED/未知 不计入
esac
tot_pass=$((ex_pass + ts_pass + api_pass))
tot_all=$((ex_total + ts_total + api_total))
if [ "$tot_all" -gt 0 ]; then
    rate=$(awk -v p="$tot_pass" -v a="$tot_all" 'BEGIN{printf "%.2f", 100.0*p/a}')
else
    rate=0.00
fi

echo
echo "================ 本地实测汇总 ================"
echo "UPSTREAM_EXAMPLES_RESULT=${EX_RESULT} (passed=${ex_pass}/${ex_total})"
echo "UPSTREAM_TESTS_RESULT=${TS_RESULT}"
echo "API_TESTS_RESULT=${API_RESULT} (assertions=${api_total} failures=${api_fail})"
echo "TOTAL_PASS_RATE=${rate}% (passed=${tot_pass} total=${tot_all})"
echo "============================================="

# ---- 5. 透传非零退出码 ----
if [ "$ex_rc" -ne 0 ] || [ "$ts_rc" -ne 0 ] || [ "$api_rc" -ne 0 ]; then
    exit 1
fi
exit 0
