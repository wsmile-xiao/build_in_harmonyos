#!/usr/bin/env bash
# test_package/test_asncounter.sh — asncounter 消费测试（import + 真实 API）
set -euo pipefail
pkg="$1"
site_pkg="${2:-}"

echo "[test] asncounter 打包完整性检查"
[ -d "$pkg/lib/python3.12/site-packages/asncounter.py" ] || \
  [ -f "$pkg/lib/python3.12/site-packages/asncounter.py" ] && echo "PASS: asncounter.py 存在" || { echo "FAIL: asncounter.py 缺失"; exit 1; }

echo "[test] import asncounter（真实 API——R9/R34）"
export PYTHONPATH="$pkg/lib/python3.12/site-packages${site_pkg:+:$site_pkg}"
# 依赖 pyasn（remote 无配方——测试环境 pip 安装——wheel 构建需要 clang）
CC=/data/service/hnp/bin/clang PATH=/data/service/hnp/bin:$PATH \
  python3 -m pip install pyasn --quiet 2>/dev/null || true
out=$(python3 -c "
import asncounter
assert hasattr(asncounter, 'main') or hasattr(asncounter, '__version__'), 'API missing'
print('PASS: import asncounter OK')
" 2>&1) && rc=0 || rc=$?
echo "$out"
if [ "$rc" -ne 0 ]; then
    echo "FAIL: import asncounter 失败（rc=$rc）"
    exit 1
fi
echo "PASS: asncounter smoke test OK"
