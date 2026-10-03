#!/bin/sh
# repro_config_guess.sh — CONFIG-GUESS-BUILD-TYPE-OHOS 双向复现脚本
# 样例库: swish-e 2.4.7（任何 bundled config.guess <2016 的 autotools 包同理）
# 用法: sh repro_config_guess.sh <源码目录> <日志输出目录> [CC]
# 约束: 日志全部重定向到文件（规避 SIGPIPE，不直接管道 head）；退出码显式捕获。
set -u

SRC=${1:?usage: $0 <source-dir> <log-dir> [CC]}
LOG=${2:?usage: $0 <source-dir> <log-dir> [CC]}
CC=${3:-clang}
BUILD_TRIPLET=aarch64-unknown-linux-gnu

mkdir -p "$LOG"
cd "$SRC" || exit 2

# ── ① 不启用 SKILL：原始 configure 应失败并命中特征 ──
./configure --disable-shared > "$LOG/repro-noskill.log" 2>&1
NOSKILL_RC=$?
grep -q "cannot guess build type" "$LOG/repro-noskill.log"
NOSKILL_HIT=$?
echo "[noskill] rc=$NOSKILL_RC signature_hit=$NOSKILL_HIT (log: $LOG/repro-noskill.log)"

# ── ② 启用 SKILL：显式 --build 三元组后 configure 应通过 ──
./configure --disable-shared --disable-nls \
  --build=$BUILD_TRIPLET --host=$BUILD_TRIPLET CC="$CC" \
  > "$LOG/repro-skill.log" 2>&1
SKILL_RC=$?
echo "[skill] rc=$SKILL_RC (log: $LOG/repro-skill.log)"

# ── 判定 ──
if [ "$NOSKILL_RC" -ne 0 ] && [ "$NOSKILL_HIT" -eq 0 ] && [ "$SKILL_RC" -eq 0 ]; then
  echo "VERDICT: PASS (不启用=失败+特征命中; 启用=通过)"
  exit 0
fi
echo "VERDICT: FAIL (noskill_rc=$NOSKILL_RC hit=$NOSKILL_HIT skill_rc=$SKILL_RC)"
exit 1
