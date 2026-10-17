#!/bin/bash
# Verify the packaged Leaflet.markercluster dist assets.
# Usage: test.sh <pkg_folder>
#
# 纯 JS 资产包无编译产物 → 验证 = 存在性 + 内容锚点 + sha256 完整性。
# 16 条核心断言 + node 语法校验 + 1 个完整消费者端到端用例（consumer/cluster_flow.js，
# node + 最小 DOM 桩 + 真实 Leaflet 运行时，走完建图→加 100 标记→聚合→放大解散→
# 移除全流程，规则12 要求）。node 不可用环境 SKIP 对应检查。
PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

D="$PKG_FOLDER/share/leaflet-markercluster"
LIC="$PKG_FOLDER/licenses"
pass=0
fail=0

chk() {
    # chk <name> <cmd...>
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "  [ok] $name"
        pass=$((pass + 1))
    else
        echo "  [FAIL] $name"
        fail=$((fail + 1))
    fi
}

# --- 存在性（dist 4 件套） ---
chk "dist min js present"     test -s "$D/leaflet.markercluster.js"
chk "dist src js present"     test -s "$D/leaflet.markercluster-src.js"
chk "dist css present"        test -s "$D/MarkerCluster.css"
chk "dist default css present" test -s "$D/MarkerCluster.Default.css"

# --- JS 内容锚点（工厂挂载点 + 版本横幅） ---
chk "src js factory anchor"   grep -q "L.MarkerClusterGroup" "$D/leaflet.markercluster-src.js"
chk "min js factory anchor"   grep -q "L.MarkerClusterGroup" "$D/leaflet.markercluster.js"
chk "src js version banner"   grep -q "Leaflet.markercluster 1.5.3" "$D/leaflet.markercluster-src.js"

# --- CSS 内容锚点 ---
chk "css anim anchor"         grep -q "\.leaflet-cluster-anim" "$D/MarkerCluster.css"
chk "css spider-leg anchor"   grep -q "\.leaflet-cluster-spider-leg" "$D/MarkerCluster.css"
chk "default css small"       grep -q "\.marker-cluster-small" "$D/MarkerCluster.Default.css"
chk "default css large"       grep -q "\.marker-cluster-large" "$D/MarkerCluster.Default.css"

# --- sourcemap 与文档 ---
chk "sourcemap min present"   test -s "$D/leaflet.markercluster.js.map"
chk "sourcemap src present"   test -s "$D/leaflet.markercluster-src.js.map"
chk "MIT licence text"        grep -qi "permission is hereby granted" "$LIC/MIT-LICENCE.txt"
chk "readme packaged"         test -s "$LIC/README.md"

# --- 安装产物与 npm dist 逐字节一致（纯字符串比对哈希列，不依赖 diff/进程替换：
#     Windows sha256sum 带 * 前缀、OHOS 上 diff 机制不稳，均取 awk 哈希列后直接比较） ---
EXPECTED='1e4e1d22972a3926f48598e0caf14e3fe7049835d428a344fed4f9e3665b3508
6837513658e18b26349b62fceb041ea917da7a496509133edc39abcc8f173c8c
614dea0a98ff3f4ead74f04918f6b1d1b9ba435c25b5fc23b21a394d1e3e4d87
61258232d98d64dc2a7b1e02130d67421bc5b9bda5994eef70228ff97570c170'
ACTUAL=$( (cd "$D" && sha256sum leaflet.markercluster.js leaflet.markercluster-src.js \
    MarkerCluster.css MarkerCluster.Default.css) 2>/dev/null | awk '{print $1}' )
if [ "$ACTUAL" = "$EXPECTED" ]; then
    echo "  [ok] installed == npm dist sha256"
    pass=$((pass + 1))
else
    echo "  [FAIL] installed == npm dist sha256"
    echo "         expected: $(echo "$EXPECTED" | tr '\n' ' ')"
    echo "         actual:   $ACTUAL"
    fail=$((fail + 1))
fi

# --- node 检查：语法校验 + 完整消费者端到端用例。OHOS 自带 node v24.13 但 V8 JIT
#     在 OHOS 上直接 SIGTRAP（errno_location 断言失败），必须加 --jitless（知识库
#     E400 记录的恢复条件）；可用性自检（探针文件 --jitless --check）通过才启用，
#     自检不过则 SKIP 不计失败。 ---
if command -v node >/dev/null 2>&1; then
    PROBE=".lmc-nodeprobe-$$.js"
    if printf 'var __lmc_probe__ = 1;\n' > "$PROBE" 2>/dev/null \
       && node --jitless --check "$PROBE" >/dev/null 2>&1; then
        rm -f "$PROBE"

        # 语法校验
        if node --jitless --check "$D/leaflet.markercluster-src.js" >/dev/null 2>&1 \
           && node --jitless --check "$D/leaflet.markercluster.js" >/dev/null 2>&1; then
            echo "  [ok] node --jitless --check syntax (both dist js)"
            pass=$((pass + 1))
        else
            echo "  [FAIL] node --jitless --check syntax"
            fail=$((fail + 1))
        fi

        # 完整消费者用例：node + 最小 DOM 桩 + 真实 Leaflet 1.9.4 运行时，
        # 端到端跑通「模块加载→建图→加 100 标记→z0 聚合（1 簇 100 子）→z15 解散
        # （100 标记各自可见）→removeLayer→整组摘除」全流程（14 个验证节点）。
        CONSUMER_DIR="$(dirname "$0")/consumer"
        if node --jitless "$CONSUMER_DIR/cluster_flow.js" "$D/leaflet.markercluster.js"; then
            echo "  [ok] consumer e2e cluster flow (14 nodes)"
            pass=$((pass + 1))
        else
            echo "  [FAIL] consumer e2e cluster flow"
            fail=$((fail + 1))
        fi
    else
        rm -f "$PROBE"
        echo "  [skip] node checks (node unusable even with --jitless)"
    fi
else
    echo "  [skip] node checks (node not available in target env)"
fi

echo "=== Results: $pass passed, $fail failed ==="
[ "$fail" -eq 0 ]
