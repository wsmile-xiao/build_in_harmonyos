#!/bin/bash
# doas 消费者探针 — 调用已安装二进制(doas 在 conanrun PATH 中)
# 三项断言,全部免 root:
#   P1  -C 合法配置   → 退出码 0(真跑 parse.y 解析器)
#   P2  -C 非法配置   → 退出码非 0(语法被拒绝)
#   P3  无参数        → stderr 出现 usage 横幅
#
# CI 66509:worker 的调用用户(uid 100)无 passwd 条目,doas 在解析
# 任何配置前先 getpwuid(self),报 "no passwd entry for self" 退出非零。
# 这使功能断言不可达，必须返回失败；不能用成功 RC 掩盖未执行测试。
set -u
fail=0

cat > doas-good.conf <<'EOF'
permit persist :wheel
permit nopass root
deny :video
EOF

cat > doas-bad.conf <<'EOF'
frobnicate all
EOF

err1=$(doas -C doas-good.conf 2>&1)
rc=$?
if [ $rc -ne 0 ]; then
  if printf '%s' "$err1" | grep -qi "no passwd entry"; then
    echo "FAIL: invoking user has no passwd entry; parser assertions were not executed."
    exit 1
  fi
  echo "FAIL P1: -C good.conf rejected"
  printf '%s\n' "$err1"
  fail=1
fi

if doas -C doas-bad.conf 2>/dev/null; then
  echo "FAIL P2: bad config accepted"
  fail=1
fi

out=$(doas 2>&1 || true)
case "$out" in
  *usage:*) : ;;
  *) echo "FAIL P3: no usage banner: $out"; fail=1 ;;
esac

if [ "$fail" -eq 0 ]; then
  echo "PROBE 3/3 PASS"
fi
exit $fail
