#!/bin/bash
# test_shellia.sh — shellia test_package（消费者视角验证）
# 断言：
#   1. share/shellia/ia 及全部 ia* 库文件已打包
#   2. 在库目录内 bash source ia 库成功（ia 内部 ia_find_lib 优先查当前目录 ia.basic）
#   3. 核心函数 ia_set2var / ia_easy_backslash 可调用且行为正确
# 用法: bash test_shellia.sh <package_folder>
# 说明: 刻意不启用 `set -e` —— check() 以命令退出码判定 PASS/FAIL，
#       非零退出码在该函数内是期望分支；启用 -e 会导致断言失败时提前退出、
#       无法完成全部断言汇总。启用 -uo + pipefail 提供未定义变量与管道保护。
set -uo pipefail

PKG="$1"
SHARE="$PKG/share/shellia"
PASS=0
FAIL=0

check() {
  local desc="$1" rc="$2"
  if [ "$rc" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "PASS: $desc"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (rc=$rc)"
  fi
}

# 1. ia* 库文件存在且非空
missing=0
for f in ia ia.array ia.basic ia.log ia.debug ia.interactive ia.check ia.highlevel; do
  if [ -f "$SHARE/$f" ] && [ -s "$SHARE/$f" ]; then
    :
  else
    echo "MISSING: $SHARE/$f"
    missing=1
  fi
done
check "ia* 8 个库文件全部存在且非空" "$missing"

# 2-4. 在库目录内 source ia 并验证核心函数
# （ia 内部 ia_find_lib 按 ./$(basename) → $0 上级 → 绝对路径顺序查找，
#   必须 cd 到库目录才能命中 ./ia.basic；send 前须避免 /usr/share/shellia 不存在）
(
  cd "$SHARE" || exit 1
  bash -c ". ./ia && echo 'source ok'" 2>/dev/null
)
check "bash source ia 库成功（库目录内）" $?

(
  cd "$SHARE" || exit 1
  bash -c ". ./ia; type ia_set2var >/dev/null 2>&1"
)
check "ia_set2var 函数可解析" $?

out=$(cd "$SHARE" && bash -c ". ./ia.basic; /bin/echo 'a\"b' | ia_easy_backslash --quote" 2>/dev/null)
[ "$out" = 'a\"b' ]
check "ia_easy_backslash --quote 转义正确 (got: $out)" $?

# 5. 0001 补丁行为锁定：ia.array base64 编解码往返（toybox base64 decode 无 -w）
out=$(cd "$SHARE" && bash -c ". ./ia.array; arr=\$(ia_arr_mk 'one two' 'three'); ia_arr_get 1 \"\$arr\"" 2>/dev/null)
[ "$out" = "one two" ]
check "ia_arr_mk/ia_arr_get base64 编解码往返正确 (got: $out)" $?

# 6. 0003 补丁行为锁定：ia.log /dev/null 日志文件不报警告（toybox touch /dev/null 被守卫跳过）
out=$(cd "$SHARE" && bash -c "ia_logfile=/dev/null; . ./ia.log; ia_check_logfile /dev/null 2>&1; echo done" 2>/dev/null)
[ "$out" = "done" ]
check "ia_check_logfile /dev/null 不产生 WARNING（0003 补丁覆盖） (got: $out)" $?

echo
echo "==== RESULT: PASS=$PASS FAIL=$FAIL ===="
[ "$FAIL" -eq 0 ] || exit 1
exit 0