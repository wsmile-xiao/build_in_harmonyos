#!/bin/sh
# test_plasma-wayland-protocols.sh — plasma-wayland-protocols 数据包消费者验证脚本
#
# 验证协议 XML 安装完整 + 每个 XML 结构合法（对齐上游 autotests 的
# scanner 校验语义：wayland-scanner 动态链 libexpat/libxml2 在 HMDFS
# 下不可执行，此处用 python3 xml.dom.minidom 做等价的 XML 良构性检查）。
# 用法：test_plasma-wayland-protocols.sh <pkg_dir>
set -eu

PKG="$1"
PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); echo "        [ok] $1"; }
fail() { FAIL=$((FAIL+1)); echo "        [fail] $1"; }

# 1. CMake Config 包存在（find_package(PlasmaWaylandProtocols) 入口；
#    上游 1.20.0 不安装 .pc，实测包产物仅 Config + XML——不虚构 .pc 断言）
if [ -f "$PKG/share/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfig.cmake" ]; then
    ok "PlasmaWaylandProtocolsConfig.cmake 存在（share/cmake 新路径）"
else
    fail "PlasmaWaylandProtocolsConfig.cmake 缺失"
fi
[ -f "$PKG/share/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfigVersion.cmake" ] \
    && ok "PlasmaWaylandProtocolsConfigVersion.cmake 存在" || fail "ConfigVersion.cmake 缺失"

# 2. Config 内 PLASMA_WAYLAND_PROTOCOLS_DIR 变量声明有效
#    （PlasmaWaylandProtocolsConfig.cmake.in: set(PLASMA_WAYLAND_PROTOCOLS_DIR
#    "@PACKAGE_KDE_INSTALL_DATADIR@/plasma-wayland-protocols")）
if grep -q "PLASMA_WAYLAND_PROTOCOLS_DIR" \
    "$PKG/share/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfig.cmake"; then
    ok "Config 声明 PLASMA_WAYLAND_PROTOCOLS_DIR 变量"
else
    fail "Config 缺 PLASMA_WAYLAND_PROTOCOLS_DIR 变量"
fi

# 3. 协议目录 + 30 个协议 XML 完整性（上游 src/CMakeLists.txt install 清单 30 项）
PDIR="$PKG/share/plasma-wayland-protocols"
if [ -d "$PDIR" ]; then
    ok "share/plasma-wayland-protocols/ 目录存在"
else
    fail "协议目录缺失: $PDIR"
fi
count=$(ls "$PDIR"/*.xml 2>/dev/null | wc -l)
if [ "$count" -ge 30 ]; then
    ok "协议 XML 数量 = $count（>=30，含 2 个向后兼容改名副本）"
else
    fail "协议 XML 数量 $count < 30"
fi

# 4. 关键协议抽查（Plasma 6.6 核心依赖）
for p in plasma-window-management kde-output-device-v2 zkde-screencast-unstable-v1 appmenu blur; do
    [ -f "$PDIR/$p.xml" ] && ok "协议 $p.xml 存在" || fail "协议 $p.xml 缺失"
done

# 5. 向后兼容改名副本（screencast.xml / plasma-virtual-desktop.xml）
[ -f "$PDIR/screencast.xml" ] && ok "向后兼容副本 screencast.xml 存在" || fail "screencast.xml 缺失"
[ -f "$PDIR/plasma-virtual-desktop.xml" ] && ok "向后兼容副本 plasma-virtual-desktop.xml 存在" || fail "plasma-virtual-desktop.xml 缺失"

# 6. 全部 XML 良构性检查（对齐上游 wayland-scanner --strict 扫描语义的
#    平台等价实现：scanner 在 HMDFS 不可执行，用标准 XML 解析器替代）
xml_bad=""
for f in "$PDIR"/*.xml; do
    if ! python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" "$f" 2>/dev/null; then
        xml_bad="$xml_bad $(basename "$f")"
    fi
done
if [ -z "$xml_bad" ]; then
    ok "全部 $count 个协议 XML 良构（python3 minidom 解析通过）"
else
    fail "XML 解析失败:$xml_bad"
fi

# 7. 版本头文件（ecm_setup_version 生成 plasma_wayland_protocols_version.h，
#    随 Config 一起安装到 Config 目录?——实际安装到 includedir；数据包无
#    include 目录属正常，仅校验 Config 引用一致）
if grep -q "PACKAGE_VERSION" \
    "$PKG/share/cmake/PlasmaWaylandProtocols/PlasmaWaylandProtocolsConfigVersion.cmake" 2>/dev/null; then
    ok "ConfigVersion 文件内容有效"
else
    fail "ConfigVersion 文件内容无效或缺失"
fi

echo "    断言统计: pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ]
