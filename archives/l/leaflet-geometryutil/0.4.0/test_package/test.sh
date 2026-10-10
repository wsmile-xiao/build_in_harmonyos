#!/bin/sh
set -eu

# 参数：$1 = leaflet.geometryutil.js 的绝对路径
GEO_JS="$1"
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"

# OHOS 沙箱禁止 mmap(PROT_EXEC)，所有 Node 进程必须禁用 JIT
export NODE_OPTIONS=--jitless

# 依赖安装到用户缓存目录（避开只读 /tmp，避免污染仓库）
DEPS_DIR="${HOME}/.cache/leaflet-geometryutil-test-deps"
if [ ! -d "$DEPS_DIR/node_modules/mocha" ] \
   || [ ! -d "$DEPS_DIR/node_modules/jsdom" ] \
   || [ ! -d "$DEPS_DIR/node_modules/leaflet" ] \
   || [ ! -d "$DEPS_DIR/node_modules/chai" ]; then
  mkdir -p "$DEPS_DIR"
  cd "$DEPS_DIR"
  npm install --no-save --silent \
    jsdom@24 mocha@10 chai@4 leaflet@0.7.2
fi

export NODE_PATH="$DEPS_DIR/node_modules"
export GEO_JS="$GEO_JS"

echo ""
echo "=========================================="
echo "  [1/2] 上游测试（60 用例，真实执行）"
echo "=========================================="
cd "$PKG_DIR"
node "$DEPS_DIR/node_modules/mocha/bin/mocha.js" \
  --require "$PKG_DIR/setup.js" \
  "$PKG_DIR/upstream-test.js"

echo ""
echo "=========================================="
echo "  [2/2] 鸿蒙专属测试"
echo "=========================================="
node "$PKG_DIR/harmony_smoke.js" "$GEO_JS"
