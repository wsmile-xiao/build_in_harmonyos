#!/bin/sh
# 消费者测试（鸿蒙特有测试 C1-C4）：直跑已安装的 CLI `paraglob-test`。
# 期望值逐条对齐上游 testing/Baseline/*（btest-diff 基线）实测读数。
#
# 用法: sh test_cli.sh <package bin dir>
# 断言计数：C1..C4 共 4 条；任一失败即非零退出。
set -eu

BINDIR="${1:?用法: sh test_cli.sh <package bin dir>}"
PT="$BINDIR/paraglob-test"

fail() { echo "[FAIL] $1"; exit 1; }

[ -f "$PT" ] || fail "安装树缺少 bin/paraglob-test: $PT"
[ -x "$PT" ] || fail "bin/paraglob-test 不可执行: $PT"

# C1 —— 上游 driver.basic_matches：模式 5 个对 "dog" 命中 4 个
out=$("$PT" -n dog "*" "d?g" "*og" "d?" "d[!wl]g" | sed -n '1p')
[ "$out" = "4" ] || fail "C1 期望 4 实得 '$out'"
echo "[ok]   C1 basic_matches count == 4"

# C2 —— 上游 driver.empty_patterns：模式 7 个对 "dog" 命中 1 个
out=$("$PT" -n dog "*" "cat" "dog?" "fish" "horse" "frog" "lion" \
      | sed -n '1p')
[ "$out" = "1" ] || fail "C2 期望 1 实得 '$out'"
echo "[ok]   C2 empty_patterns count == 1"

# C3 —— 无可命中模式时为 0
out=$("$PT" -n zzz "cat" "dog" | sed -n '1p')
[ "$out" = "0" ] || fail "C3 期望 0 实得 '$out'"
echo "[ok]   C3 no-match count == 0"

# C4 —— 上游 driver.serial 两条基线均为 passed（序列化往返自校验）
out=$("$PT" -s dog "*" "d?g" "*og" "d?" "d[!wl]g")
[ "$out" = "passed" ] || fail "C4 期望 passed 实得 '$out'"
echo "[ok]   C4 serialize round-trip == passed"

echo "paraglob CLI consumer: PASS (4/4)"
