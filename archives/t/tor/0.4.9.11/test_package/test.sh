#!/bin/bash
# test_package/test.sh — tor 0.4.9.11 消费者冒烟测试
# 4 个用例全部离线可跑（不触网、不建监听）：版本报告 / 配置校验 /
# 配置项枚举 / 口令哈希（后者运行期真实调用 OpenSSL 完成 S2K；tor 二进制
# 运行期动态加载 libevent，用例全过即依赖链可用）。
# 每个用例输出一行 "case N: <描述>: PASS/FAIL"；最后 "RESULT: passed/total"，
# 供 test_package/conanfile.py 解析并上报 HMBS_TEST_PACKAGE_RESULT。
#
# 注意（真机实测 2026-10-03）：本脚本在 `set -o pipefail` 下运行，禁止
# `… | grep -q`——grep 命中即提前退出会让仍在写输出的上游进程吃到 SIGPIPE
# （rc=141），pipefail 令整个管道判失败，成功案例被随机误判为 FAIL
# （run5 挂 case1、复跑挂 case3，同一构建同一环境）。统一改为「先把输出整体
# 捕获到变量，再用 grep -c（读满输入、不提前退出）计数匹配」。
set -uo pipefail

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tor-test.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT
total=0
passed=0

step() { # step "<描述>" <函数名>
  local desc="$1"
  shift
  local log="$TMP/case.log"
  if "$@" >"$log" 2>&1; then
    total=$((total + 1))
    passed=$((passed + 1))
    echo "case $total: $desc: PASS"
  else
    total=$((total + 1))
    echo "case $total: $desc: FAIL"
    sed 's/^/    /' "$log" | tail -15
  fi
}

# 以下 4 个用例统一模式：捕获全部输出 → grep -c 计数（读满输入）→ 失败时
# 回吐原始输出供诊断。捕获命令失败（如加载器错误）不掩盖，交由计数裁决。

case_version() {
  local V rc
  V=$(tor --version 2>&1) || true
  test "$(printf '%s\n' "$V" | grep -c 'Tor version 0\.4\.9\.11')" -gt 0
  rc=$?
  [ "$rc" -eq 0 ] || printf '%s\n' "$V"
  return "$rc"
}

case_config() {
  mkdir -p "$TMP/data"
  printf 'DataDirectory %s/data\nSocksPort 0\n' "$TMP" >"$TMP/torrc"
  tor --verify-config -f "$TMP/torrc"
}

case_options() {
  local V rc
  V=$(tor --list-torrc-options 2>&1) || true
  test "$(printf '%s\n' "$V" | grep -c '^SocksPort$')" -gt 0
  rc=$?
  [ "$rc" -eq 0 ] || printf '%s\n' "$V"
  return "$rc"
}

case_hashpw() {
  local V rc
  V=$(tor --hash-password tor-test-pw 2>&1) || true
  test "$(printf '%s\n' "$V" | grep -c '^16:')" -gt 0
  rc=$?
  [ "$rc" -eq 0 ] || printf '%s\n' "$V"
  return "$rc"
}

step "tor --version 报告 0.4.9.11" case_version
step "tor --verify-config 接受最小 torrc" case_config
step "tor --list-torrc-options 含 SocksPort" case_options
step "tor --hash-password 输出 16: 前缀哈希" case_hashpw

echo "RESULT: $passed/$total"
[ "$passed" -eq "$total" ]
