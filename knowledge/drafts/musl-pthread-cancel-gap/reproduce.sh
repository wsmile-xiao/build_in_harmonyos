#!/usr/bin/env sh
# 复现：OHOS musl libc 的 POSIX 线程取消 API 缺口（pthread_cancel 族）
#
# 做三件事：
#   1. 源码侧识别 + libc/空壳库探针（调用同目录 detect_pthread_cancel_gap.py）
#   2. 最小链接探针：一个只调用 pthread_cancel 的小程序，用 OHOS clang 链接，
#      复现 `undefined symbol: pthread_cancel`（证明缺口真实存在）
#   3. 可选：样例库（xmcd 3.3.2）干净环境 conan create 全量复现
#
# 用法：
#   sh reproduce.sh [--src <源码目录>] [--libc <libc.so>] [--log <日志文件>] [--repo <仓库根>]
#   CONAN_REPRO=1 sh reproduce.sh --src <源码目录> --repo <仓库根>
#
# 约束：日志一律落文件（不接管道到 head/tail，规避 SIGPIPE）；无硬编码本机路径。
set -eu
# pipefail 仅在解释器支持时启用（POSIX sh / dash 不支持 -o pipefail，硬写会在启动即退出）
if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi

SRC=""
LIBC=""
LOG=""
REPO=""
while [ $# -gt 0 ]; do
    case "$1" in
        --src)  SRC="$2";  shift 2 ;;
        --libc) LIBC="$2"; shift 2 ;;
        --log)  LOG="$2";  shift 2 ;;
        --repo) REPO="$2"; shift 2 ;;
        -h|--help) sed -n '1,20p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -n "$SRC" ] || SRC="${REPO:-$HERE}"
# 临时产物走 mktemp 私有目录：固定可预测路径会被并发运行互踩，也易被预置符号链接
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/pthread-cancel-gap.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT INT TERM
[ -n "$LOG" ] || LOG=$(mktemp "${TMPDIR:-/tmp}/pthread-cancel-gap-repro.XXXXXX.log")
: > "$LOG"

say() { printf '%s\n' "$*" >> "$LOG"; }
run() { printf '\n$ %s\n' "$*" >> "$LOG"; "$@" >> "$LOG" 2>&1 || printf '[rc=%s]\n' "$?" >> "$LOG"; }

say "=== OHOS musl pthread_cancel 族缺口复现  $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
say "src=$SRC libc=${LIBC:-<auto>}"

# --- 1. 识别 + 探针 -------------------------------------------------------
say ""
say "--- [1] 检测脚本（源码侧调用清点 + libc/空壳库探针）---"
if [ -n "$LIBC" ]; then
    run python3 "$HERE/detect_pthread_cancel_gap.py" --src "$SRC" --libc "$LIBC"
else
    run python3 "$HERE/detect_pthread_cancel_gap.py" --src "$SRC"
fi

# --- 2. 最小链接探针 ------------------------------------------------------
say ""
say "--- [2] 最小链接探针（pthread_cancel 符号解析）---"
CC=""
for cand in "$(command -v clang 2>/dev/null || true)" \
            /data/service/hnp/bin/clang; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then CC="$cand"; break; fi
done
if [ -z "$CC" ]; then
    say "SKIP: 未找到 clang（可用 OHOS SDK 自带 clang 重跑）"
else
    PROBE_SRC="$WORKDIR/pthread_cancel_probe.c"
    cat > "$PROBE_SRC" <<'EOF'
#include <pthread.h>
int main(void) {
    pthread_t t = pthread_self();
    (void) pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, 0);
    return pthread_cancel(t);
}
EOF
    say "编译器: $CC"
    # 链接探针：只链接 libc（不 -lpthread），复现 undefined symbol
    run "$CC" --target=aarch64-linux-ohos -c "$PROBE_SRC" -o "$WORKDIR/pthread_cancel_probe.o"
    say "（编译通过说明头文件声明存在；下一步链接暴露符号缺口）"
    run "$CC" --target=aarch64-linux-ohos "$WORKDIR/pthread_cancel_probe.o" -o "$WORKDIR/pthread_cancel_probe"
    say "注意：若上面出现 'undefined symbol: pthread_cancel'，即为本缺口的最简复现。"
    say "对照：pthread_exit / pthread_detach / pthread_cond_timedwait 在 libc 中存在（见 [1] 探针输出）。"
fi

# --- 3. 可选：样例库全量复现 ---------------------------------------------
if [ "${CONAN_REPRO:-0}" = "1" ] && [ -n "$REPO" ]; then
    say ""
    say "--- [3] 样例库（xmcd 3.3.2）干净环境 conan create ---"
    run conan create "$REPO/archives/x/xmcd/3.3.2" \
        -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" \
        -pr:b="$REPO/ci/conan/profiles/ohos-aarch64"
    say "样例库配方以 -DHAVE_PTHREAD_CANCEL=0 关闭取消点，用 PTHR_SELF_ABORT 间接层"
    say "（=0 时回退 pthread_exit）与 cdda_pthr_kill 降级完成适配。"
fi

say ""
say "日志：$LOG"
printf 'reproduce done -> %s\n' "$LOG"
