#!/usr/bin/env bash
# Imake/xmkmf 遗产 X11 库适配 — 复现脚本（知识库拓展；样例库 xli 1.17.0-20061110）
#
# 用途：一键复现「Imake 遗产库在 OHOS（无 imake/xmkmf + musl libc）下的识别与修复证据」。
# 用法：bash reproduce.sh [--src <源码目录>] [--libc <libc.so>] [--log <日志文件>] [--repo <仓库根>]
# 缺省：--src=$PWD；--log=$PWD/imake-legacy-repro.log；--libc 取 $OHOS_SDK_SYSROOT 推导
#
# 约定（对齐仓库脚本规范）：
#   * 安全模式 set -euo pipefail；对"非零即预期"的调用显式捕获 rc（检测器命中返回 1）
#   * 全部输出重定向到日志文件，不接 head/grep 管道（规避 SIGPIPE）
#   * 不硬编码本地绝对路径：脚本按自身位置定位同级检测器；SDK 路径读 OHOS_SDK_SYSROOT
#   * 只读操作；样例库 conan create 仅在 CONAN_REPRO=1 时显式执行
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC_DIR=$PWD
LIBC=${OHOS_SDK_SYSROOT:+$OHOS_SDK_SYSROOT/usr/lib/aarch64-linux-ohos/libc.so}
LOG=$PWD/imake-legacy-repro.log
REPO_ROOT=${OHC_PROJECT_DIR:-}

while [ $# -gt 0 ]; do
    case "$1" in
        --src)  SRC_DIR=$2; shift 2 ;;
        --libc) LIBC=$2; shift 2 ;;
        --log)  LOG=$2; shift 2 ;;
        --repo) REPO_ROOT=$2; shift 2 ;;
        -h|--help)
            echo "usage: bash reproduce.sh [--src DIR] [--libc LIBC] [--log FILE] [--repo REPO_ROOT]"
            exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

{
    echo "=== Imake/xmkmf 遗产 X11 库适配复现 ($(date -u '+%Y-%m-%dT%H:%M:%SZ')) ==="
    echo "src  : $SRC_DIR"
    echo "libc : ${LIBC:-(未提供，跳过符号探针)}"
    echo
    echo "--- [1/4] 工具链现状：imake/xmkmf 是否可用 ---"
    for t in imake xmkmf clang gcc nm python3; do
        p=$(command -v "$t" 2>/dev/null || true)
        if [ -n "$p" ]; then echo "  $t -> $p"; else echo "  $t -> (缺失)"; fi
    done
    echo
    echo "--- [2/4] 构建系统与 libc 缺口识别 ---"
    if [ -f "$SCRIPT_DIR/detect_imake_legacy.py" ]; then
        # 检测器退出码：0=未命中 1=命中（非错误）2=参数错误 —— 显式捕获，不触发 set -e
        rc=0
        if [ -n "$LIBC" ]; then
            python3 "$SCRIPT_DIR/detect_imake_legacy.py" --src "$SRC_DIR" --libc "$LIBC" || rc=$?
        else
            python3 "$SCRIPT_DIR/detect_imake_legacy.py" --src "$SRC_DIR" || rc=$?
        fi
        echo "detect rc=$rc"
    else
        echo "  ERROR: 未找到同级检测器 $SCRIPT_DIR/detect_imake_legacy.py"
    fi
    echo
    echo "--- [3/4] 目标 libc 符号探针（BSD 遗留函数）---"
    if [ -n "$LIBC" ] && [ -f "$LIBC" ] && command -v nm >/dev/null 2>&1; then
        NM_OUT=$LOG.nm.tmp
        nm -D --defined-only "$LIBC" > "$NM_OUT" 2>&1
        for f in rindex index bcopy bzero bcmp; do
            n=$(grep -cw "$f" "$NM_OUT" || true)
            echo "  $f -> defined symbols: $n"
        done
        rm -f "$NM_OUT"
        echo "  (缺失函数需逐函数最小定向替换，见 README 处理策略 S1/S3)"
    else
        echo "  (跳过：未提供 --libc/OHOS_SDK_SYSROOT 或 nm 不可用)"
    fi
    echo
    echo "--- [4/4] 样例库 xli 1.17.0-20061110 复现命令 ---"
    echo "  conan create archives/x/xli/1.17.0-20061110 \\"
    echo "      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \\"
    echo "      > conan-create-xli.log 2>&1"
    if [ "${CONAN_REPRO:-0}" = "1" ]; then
        if [ -z "$REPO_ROOT" ]; then
            d=$PWD
            while [ "$d" != "/" ]; do
                if [ -d "$d/archives/x/xli/1.17.0-20061110" ]; then REPO_ROOT=$d; break; fi
                d=$(dirname -- "$d")
            done
        fi
        if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT/archives/x/xli/1.17.0-20061110" ]; then
            echo "  [执行] 仓库根=$REPO_ROOT"
            rc=0
            ( cd "$REPO_ROOT" && conan create archives/x/xli/1.17.0-20061110 \
                -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 ) \
                > "$LOG.conan-create" 2>&1 || rc=$?
            echo "  [执行] conan create rc=$rc（完整日志：$LOG.conan-create）"
        else
            echo "  [跳过] 未定位到仓库根（可用 --repo 指定）"
        fi
    else
        echo "  (未执行；设 CONAN_REPRO=1 时本脚本会实际运行并写入 $LOG.conan-create)"
    fi
    echo
    echo "=== 完成；完整日志：$LOG ==="
} > "$LOG" 2>&1

# 摘要只回一行，避免调用方再开管道（规避 SIGPIPE）
echo "repro done -> $LOG"
