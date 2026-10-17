#!/usr/bin/env bash
# 消费者测试（test_package）：验证已安装的 rtpengine 二进制实质可用
set -eu

# 主 daemon：真实执行 + 版本断言（实质依赖被测包，非 print 空壳）
# 注：rtpengine 的 --version 输出走 stderr（glib 风格），须 2>&1 捕获
out=$(rtpengine --version 2>&1)
echo "$out"
case "$out" in
  *26.0.1.15*) ;;
  *) echo "FAIL: version mismatch in: $out" >&2; exit 1 ;;
esac

# 控制 CLI 脚本存在性（perl 脚本，shebang 已适配 env perl；command -v 走 PATH）
command -v rtpengine-ctl
command -v rtpengine-ng-client

echo "test_package: PASS"
