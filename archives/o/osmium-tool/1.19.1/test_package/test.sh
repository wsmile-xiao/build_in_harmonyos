#!/data/service/hnp/bin/bash
# test_package/test.sh — 消费者视角验证：直接使用安装后的 `osmium` 可执行文件。
#
# 覆盖：版本契约 / 顶层与子命令帮助（纯 IO 退出路径，无显示依赖）/
#       XML→OPL 解析 / XML→PBF 写出与 fileinfo 读回 / PBF→OPL 往返一致性 /
#       tags-filter 过滤语义。
#
# 注意：所有调用统一 `</dev/null` 并加 timeout —— CI worker 的 stdin 是打开的
# 管道，会从 STDIN 读取的程序可能永久阻塞（osmcoastline 教训）。
set -euo pipefail

WORK="$(pwd)/osmium-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0

ok() { echo "PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# has <name> <needle> <file>  —— 断言 file 中存在 needle
has() {
    if [ -f "$3" ] && grep -qF -- "$2" "$3"; then ok "$1"; else bad "$1 (缺 '$2')"; fi
}

# run <log-prefix> <cmd...>  —— 执行并把 stdout+stderr 落到 <log-prefix>.log
run() {
    _log="$1"
    shift
    timeout 60 "$@" </dev/null >"${_log}.log" 2>&1
}

echo "[test] 1/8 osmium --version"
if run "$WORK/version" osmium --version; then ok "osmium --version 退出码 0"; else bad "osmium --version rc=$?"; fi
has "版本契约为 1.19.1" "osmium version 1.19.1" "$WORK/version.log"

echo "[test] 2/8 osmium --help"
if run "$WORK/help" osmium --help; then ok "osmium --help 退出码 0"; else bad "osmium --help rc=$?"; fi
has "顶层帮助列出 COMMANDS" "COMMANDS:" "$WORK/help.log"

echo "[test] 3/8 osmium cat -h"
if run "$WORK/cathelp" osmium cat -h; then ok "osmium cat -h 退出码 0"; else bad "osmium cat -h rc=$?"; fi
has "cat 子命令用法" "Usage: osmium cat" "$WORK/cathelp.log"

cat > "$WORK/in.osm" <<'OSM'
<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="osmium-tool-test">
  <node id="1" version="1" timestamp="2020-01-01T00:00:00Z" lat="52.0" lon="13.0"/>
  <node id="2" version="1" timestamp="2020-01-01T00:00:00Z" lat="52.1" lon="13.1"/>
  <way id="10" version="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="residential"/>
  </way>
</osm>
OSM

echo "[test] 4/8 XML -> OPL"
if run "$WORK/opl" osmium cat --no-progress -f opl "$WORK/in.osm"; then ok "XML→OPL 退出码 0"; else bad "XML→OPL rc=$?"; fi
has "OPL 输出包含 node 1" "n1 " "$WORK/opl.log"
has "OPL 输出包含 way 10" "w10 " "$WORK/opl.log"
has "OPL 输出包含 highway 标签" "highway=residential" "$WORK/opl.log"

echo "[test] 5/8 XML -> PBF"
if run "$WORK/pbf" osmium cat --no-progress -f pbf -o "$WORK/out.pbf" "$WORK/in.osm"; then ok "XML→PBF 退出码 0"; else bad "XML→PBF rc=$?"; fi

echo "[test] 6/8 fileinfo 读回 PBF"
if run "$WORK/finfo" osmium fileinfo -e "$WORK/out.pbf"; then ok "fileinfo 退出码 0"; else bad "fileinfo rc=$?"; fi
has "PBF 中节点数为 2" "Number of nodes: 2" "$WORK/finfo.log"
has "PBF 中 way 数为 1" "Number of ways: 1" "$WORK/finfo.log"

echo "[test] 7/8 PBF -> OPL 往返一致"
if run "$WORK/opl2" osmium cat --no-progress -f opl "$WORK/out.pbf"; then ok "PBF→OPL 退出码 0"; else bad "PBF→OPL rc=$?"; fi
if [ -f "$WORK/opl.log" ] && cmp -s "$WORK/opl.log" "$WORK/opl2.log"; then
    ok "PBF→OPL 与 XML→OPL 逐字节一致"
else
    bad "PBF→OPL 与 XML→OPL 不一致"
fi

echo "[test] 8/8 tags-filter 过滤语义"
if run "$WORK/filter" osmium tags-filter --no-progress -f opl -o "$WORK/filtered.opl" "$WORK/in.osm" w/highway; then ok "tags-filter 退出码 0"; else bad "tags-filter rc=$?"; fi
has "过滤结果保留 way 10" "w10 " "$WORK/filtered.opl"

echo "CONSUMER_TESTS passed=$PASS failed=$FAIL"
test "$FAIL" -eq 0
