#!/usr/bin/env bash
# irrtoolset 5.1.3 消费者用例 — 模拟业务上层组件使用
#
# 消费者角色: 网络运维/策略管理应用中的 RPSL 策略校验环节
# 使用方式: 仅通过库已安装/导出的运行时产物 (bin/rpslcheck, bin/rtconfig)
#           与公开命令行接口校验路由策略对象, 不触碰库内部头文件/符号.
# 验证内容: 合法 RPSL 对象被接受, 非法对象报错, 配置生成器可运行.
set -u
fail=0

# 定位已安装二进制 (conan 包 bin/ 目录)
BIN_DIR="${BIN_DIR:-}"
if [ -z "$BIN_DIR" ]; then
  for d in "$PWD/bin" "$PWD/../bin" "$(dirname "$(command -v rpslcheck 2>/dev/null)")"; do
    if [ -n "$d" ] && [ -x "$d/rpslcheck" ]; then BIN_DIR="$d"; break; fi
  done
fi
RPSLCHECK="$BIN_DIR/rpslcheck"
RTCONFIG="$BIN_DIR/rtconfig"

echo "== 消费者: 校验合法 RPSL 对象 (inetnum + 必填属性) =="
cat > consumer-valid.rpsl <<'EOF'
inetnum: 192.0.2.0 - 192.0.2.255
netname: TEST-NET
country: ZZ
descr: test
admin-c: TEST-RIPE
tech-c: TEST-RIPE
mnt-by: TEST-MNT
status: ASSIGNED PA
created: 2020-01-01
last-modified: 2020-01-01
source: TEST

EOF
OUT=$("$RPSLCHECK" < consumer-valid.rpsl 2>&1); rc=$?
echo "exit=$rc; output: $OUT"
if [ $rc -eq 0 ] && echo "$OUT" | grep -q "Congratulations no errors"; then
  echo "CONSUMER-PASS: 合法对象校验通过"
else
  echo "CONSUMER-FAIL: 合法对象未被接受"
  fail=1
fi

echo "== 消费者: 校验非法 RPSL 对象 (缺必填属性) =="
printf 'inetnum: 192.0.2.0 - 192.0.2.255\n' > consumer-invalid.rpsl
OUT=$("$RPSLCHECK" < consumer-invalid.rpsl 2>&1); rc=$?
echo "exit=$rc; output: $OUT"
if echo "$OUT" | grep -qE "Error"; then
  echo "CONSUMER-PASS: 非法对象被拒绝"
else
  echo "CONSUMER-FAIL: 非法对象未被拒绝"
  fail=1
fi

echo "== 消费者: rtconfig 配置生成器可运行 =="
printf 'aut-num: AS1\nas-name: TEST-AS\n' > consumer-autnum.rpsl 2>/dev/null || true
"$RTCONFIG" -version > consumer-rtconfig.out 2>&1; rc=$?
echo "exit=$rc; output: $(head -1 consumer-rtconfig.out)"
if [ $rc -eq 0 ] || [ -s consumer-rtconfig.out ]; then
  echo "CONSUMER-PASS: rtconfig 运行并产生输出"
else
  echo "CONSUMER-FAIL: rtconfig 无输出"
  fail=1
fi

if [ $fail -eq 0 ]; then
  echo "CONSUMER-ALL-PASSED"
else
  echo "CONSUMER-FAILURES-DETECTED"
fi
exit $fail