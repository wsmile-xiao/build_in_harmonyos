#!/bin/bash
# fakeroot 1.37.1.2 消费测试——--version 不依赖真实 root 权限
set -euo pipefail
pkg="$1"
[ -f "$pkg/bin/fakeroot" ] || { echo "FAIL: bin/fakeroot 缺失"; exit 1; }
echo "[test] fakeroot 打包完整性检查"
echo "PASS: bin/fakeroot 存在"
# P3-2（aireview）：核心 LD_PRELOAD 拦截机制依赖 libfakeroot.so——打包完整性补充检查
if find "$pkg" \( -name "libfakeroot.so*" -o -name "libfaked.so*" \) 2>/dev/null | grep -q .; then
    echo "PASS: libfakeroot.so 存在"
else
    echo "FAIL: libfakeroot.so 缺失"
    exit 1
fi
echo "[test] fakeroot --version 运行"
out=$("$pkg/bin/fakeroot" --version 2>&1) && rc=0 || rc=$?
# P2（aireview）：rc 必须参与通过判定——仅 out 非空但 rc!=0（损坏包）也必须 FAIL，
# 否则 CI L0c 门禁会放行损坏的安装包（libfakeroot.so 加载失败等）
if [ "$rc" -eq 0 ] && [ -n "$out" ]; then
    echo "PASS: fakeroot --version 有输出（rc=$rc）"
else
    echo "FAIL: fakeroot --version 失败（rc=$rc, out=$out）"
    exit 1
fi
echo "PASS: fakeroot smoke test OK"
