#!/usr/bin/env bash
# libfstlookahead 1.8.4 test_package 产物/头文件冒烟检查（鸿蒙侧新增用例）。
# 校验包内确实交付了 LookAheadFst 扩展库与本扩展的头文件声明；
# 运行期 API 行为由同目录 lookahead_consumer.cc 现场编译执行覆盖。
set -euo pipefail

lib="$1"
matcher_header="$2"
matcher_fst_header="$3"

checks=0
ok() { checks=$((checks + 1)); echo "ok   $1"; }
bad() { checks=$((checks + 1)); echo "FAIL $1"; exit 1; }

[ -e "$lib" ] || bad "packaged lookahead library exists: $lib"
ok "packaged lookahead library exists"

[ -f "$matcher_header" ] || bad "packaged header exists: $matcher_header"
ok "packaged lookahead-matcher.h exists"

[ -f "$matcher_fst_header" ] || bad "packaged header exists: $matcher_fst_header"
ok "packaged matcher-fst.h exists"

grep -q "class ArcLookAheadMatcher" "$matcher_header" || bad "lookahead-matcher.h declares ArcLookAheadMatcher"
ok "lookahead-matcher.h declares ArcLookAheadMatcher"

grep -q "class LookAheadMatcherBase" "$matcher_header" || bad "lookahead-matcher.h declares LookAheadMatcherBase"
ok "lookahead-matcher.h declares LookAheadMatcherBase"

grep -q "LookAheadLabel" "$matcher_header" || bad "lookahead-matcher.h declares LookAheadLabel"
ok "lookahead-matcher.h declares LookAheadLabel"

grep -q "arc_lookahead_fst_type" "$matcher_fst_header" || bad "matcher-fst.h declares arc_lookahead_fst_type"
ok "matcher-fst.h declares arc_lookahead_fst_type"

grep -q "StdArcLookAheadFst" "$matcher_fst_header" || bad "matcher-fst.h declares StdArcLookAheadFst"
ok "matcher-fst.h declares StdArcLookAheadFst"

case "$lib" in
  *.so|*.so.*|*.dylib) echo "lookahead shared artifact: $(basename "$lib")" ;;
  *.a) echo "lookahead static artifact: $(basename "$lib")" ;;
  *) bad "unexpected artifact name: $(basename "$lib")" ;;
esac
ok "artifact kind recognised"

echo "PASS libfstlookahead artifacts and headers ($checks/$checks checks)"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"check_libfstlookahead.sh\",\"checks\":$checks,\"failed\":0}"
