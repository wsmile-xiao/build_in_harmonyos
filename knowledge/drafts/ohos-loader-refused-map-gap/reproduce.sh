#!/usr/bin/env bash
# 端到端复现脚本：OHOS 设备「依赖二进制存在却被拒绝映射」（知识包 ohos-loader-refused-map-gap）
#
# 用法
#   # ① 已知被拒依赖（本知识包实测案例：Xft/fontconfig 链）
#   bash reproduce.sh --libpath <conan 缓存 .../p/lib 目录，可冒号分隔多个>
#
#   # ② 用被测包自带的消费者二进制复现（最贴近真实场景，无需编译器）
#   bash reproduce.sh --consumer <消费者二进制> --libpath <.../p/lib>
#
#   # ③ 指定要探测的 soname（默认 libXft.so.2 libfontconfig.so.1）
#   bash reproduce.sh --soname libXft.so.2 --libpath <...>
#
# 退出码（与 detect_loader_refused_map.py 对齐）
#   0 复现成功：依赖存在但被拒绝映射（设备映射策略面）
#   1 真缺库/真缺陷（点名库解析不到，或 ELF 不可用）
#   2 未复现：本环境依赖可正常映射（无该策略，属正常环境）
#
# 约束：不用管道接 head/tail（规避 SIGPIPE）；日志一律落文件后再判读；
#       不写死本机绝对路径（全部来自参数/环境变量）。

set -euo pipefail

LIBPATH="${LD_LIBRARY_PATH:-}"
CONSUMER=""
SONAMES="libXft.so.2 libfontconfig.so.1"
CC_BIN="${CC:-cc}"

while [ $# -gt 0 ]; do
    case "$1" in
        --libpath) LIBPATH="${2:?--libpath 需要目录}"; shift 2 ;;
        --consumer) CONSUMER="${2:?--consumer 需要二进制路径}"; shift 2 ;;
        --soname) SONAMES="$2"; shift 2 ;;
        --cc) CC_BIN="$2"; shift 2 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
done

[ -n "$LIBPATH" ] || { echo "需要 --libpath（或预先设置 LD_LIBRARY_PATH）" >&2; exit 2; }

DETECT="$(cd "$(dirname "$0")" && pwd)/detect_loader_refused_map.py"
[ -f "$DETECT" ] || { echo "缺少判据脚本: $DETECT" >&2; exit 2; }

TMPBASE="${TMPDIR:-${HOME:-/tmp}}"
mkdir -p "$TMPBASE" 2>/dev/null || true
WORK="$(mktemp -d "$TMPBASE/loader-refused-repro.XXXXXX" 2>/dev/null)" || WORK=""
[ -n "$WORK" ] || { echo "无可用临时目录" >&2; exit 2; }
trap 'rm -rf "$WORK"' EXIT INT TERM

RUNLOG="$WORK/run.log"
echo "== 复现环境 =="
echo "   库路径 : $LIBPATH"
echo "   临时目录: $WORK"

# --- 1. 准备被测可执行文件 ------------------------------------------------
if [ -z "$CONSUMER" ]; then
    consumer_rc=0
    cat > "$WORK/consumer.c" <<'EOF'
/* 最小消费者：不调用任何库函数，仅通过 DT_NEEDED 携带目标依赖，
   以便在 exec 阶段触发加载器行为（这正是本知识包要复现的路径）。 */
int main(void) { return 0; }
EOF
    LINKARGS=""
    # 注意：-L 不接受冒号分隔的多目录，须逐目录展开（早期版本用 -L"$LIBPATH" 会链接失败）
    IFS_OLD="$IFS"; IFS=':'
    for d in $LIBPATH; do
        [ -n "$d" ] && LINKARGS="$LINKARGS -L$d"
    done
    IFS="$IFS_OLD"
    for so in $SONAMES; do
        LINKARGS="$LINKARGS -Wl,--no-as-needed -l:$so"
    done
    # shellcheck disable=SC2086
    "$CC_BIN" -o "$WORK/consumer" "$WORK/consumer.c" $LINKARGS > "$WORK/compile.log" 2>&1 || consumer_rc=$?
    if [ "$consumer_rc" -ne 0 ]; then
        echo "-- 编译最小消费者失败（rc=$consumer_rc），改用 ctypes 真实探测路径 --"
        cat "$WORK/compile.log" >&2
        exec python3 "$DETECT" --probe $SONAMES --lib-path "$LIBPATH"
    fi
    CONSUMER="$WORK/consumer"
fi

# --- 2. 运行消费者，捕获加载器行为 ---------------------------------------
set +e
LD_LIBRARY_PATH="$LIBPATH" "$CONSUMER" > "$RUNLOG" 2>&1
RC=$?
set -e
echo "== 消费者退出码: $RC =="

if [ "$RC" -eq 0 ]; then
    echo "未复现：本环境的依赖可正常映射（无该设备策略）——属正常环境，无需本知识包介入。"
    exit 2
fi

echo "---- 消费者输出 ----"
cat "$RUNLOG"
echo "--------------------"

# --- 3. 判据：拒绝映射 vs 真缺库 -----------------------------------------
set +e
python3 "$DETECT" --log "$RUNLOG" --lib-path "$LIBPATH" --probe-named
DET=$?
set -e
echo "== 判据退出码: $DET （0=拒绝映射 / 1=真缺库 / 2=无加载错误）=="
exit "$DET"
