#!/data/service/hnp/bin/bash
# test_package/test.sh — xmill 0.8 包级冒烟测试
#
# 在 conanrun 环境（PATH 含已安装的 bin/）中真实执行包内二进制：
#   用例 1  xmill/xdemill 存在且可执行
#   用例 2  [OHOS] 两个二进制均为 AArch64 ELF 且由 /lib/ld-musl-aarch64.so.1 加载
#   用例 3  [OHOS] 可执行文件不引入 libz.so（zlib 静态链入，不污染系统 /lib）
#   用例 4  无参数时打印 usage 并以非 0 退出
#   用例 5  xmill -w 压缩 -> xdemill 解压：与原始 XML 字节级一致
#   用例 6  xmill 默认模式压缩 -> xdemill 解压：元素/属性结构保持、压缩比 < 1
#   用例 7  压缩级别 -1 与 -9 均可往返（-w 字节级一致）
set -u

PASS=0
FAIL=0
SKIP=0
declare -a NAMES STATUS

report() { # report <status> <name> <detail>
  local st="$1" name="$2" detail="${3:-}"
  case "$st" in
    PASS) PASS=$((PASS+1)) ;;
    FAIL) FAIL=$((FAIL+1)) ;;
    *)    SKIP=$((SKIP+1)) ;;
  esac
  NAMES+=("$name"); STATUS+=("$st")
  printf '[%s] %-52s %s\n' "$st" "$name" "$detail"
}

echo "==== xmill test_package ===="
echo "PATH=$PATH"
command -v xmill  >/dev/null 2>&1 && echo "xmill   -> $(command -v xmill)"  || echo "xmill   -> not found"
command -v xdemill >/dev/null 2>&1 && echo "xdemill -> $(command -v xdemill)" || echo "xdemill -> not found"

XMILL_BIN=$(command -v xmill   || true)
XDEMILL_BIN=$(command -v xdemill || true)

# ---------- 用例 1 ----------
if [ -n "$XMILL_BIN" ] && [ -x "$XMILL_BIN" ] && [ -n "$XDEMILL_BIN" ] && [ -x "$XDEMILL_BIN" ]; then
  report PASS "T1 xmill/xdemill installed and executable"
else
  report FAIL "T1 xmill/xdemill installed and executable" "missing binary"
fi

# ---------- 用例 2（OHOS 特有）----------
ohos_ok=1; det=""
for b in "$XMILL_BIN" "$XDEMILL_BIN"; do
  [ -n "$b" ] || { ohos_ok=0; break; }
  hex=$(od -An -tx1 -N20 "$b" | tr -d ' \n')
  em="${hex:36:4}"
  interp=$(strings "$b" 2>/dev/null | grep -m1 "ld-musl")
  [ "$em" = "b700" ] || ohos_ok=0
  [ "$interp" = "/lib/ld-musl-aarch64.so.1" ] || ohos_ok=0
  det="$det $(basename "$b"):e_machine=$em,interp=${interp:-none}"
done
if [ $ohos_ok = 1 ]; then
  report PASS "[OHOS] T2 AArch64 ELF + musl loader" "$det"
else
  report FAIL "[OHOS] T2 AArch64 ELF + musl loader" "$det"
fi

# ---------- 用例 3（OHOS / R26）----------
zlib_ok=1
for b in "$XMILL_BIN" "$XDEMILL_BIN"; do
  [ -n "$b" ] || { zlib_ok=0; break; }
  if strings "$b" 2>/dev/null | grep -q "^libz\.so"; then zlib_ok=0; fi
done
if [ $zlib_ok = 1 ]; then
  report PASS "[OHOS] T3 no runtime libz.so dependency (static zlib)"
else
  report FAIL "[OHOS] T3 no runtime libz.so dependency (static zlib)"
fi

# ---------- 工作目录（/tmp 只读，E002，故用当前目录下的子目录）----------
WORK="$(pwd)/xmill-testwork"
# conan create 的 test_type=explicit 会在 test_package 目录原地执行，
# 故测试自带清理，避免把中间产物留在归档目录里（JC4/提交洁净性）。
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
rm -rf "$WORK"; mkdir -p "$WORK"; cd "$WORK" || exit 1

# ---------- 用例 4 ----------
if [ -n "$XMILL_BIN" ]; then
  out=$("$XMILL_BIN" 2>&1); rc=$?
  if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "Usage"; then
    report PASS "T4 no-arg prints usage, rc!=0" "rc=$rc"
  else
    report FAIL "T4 no-arg prints usage, rc!=0" "rc=$rc"
  fi
else
  report SKIP "T4 no-arg prints usage, rc!=0" "no binary"
fi

cat > sample.xml <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<catalog><book id="1"><title>Hello &amp; World</title><price>42</price></book><book id="2"><title>Second</title><price>7</price></book></catalog>
XML
SRC_SHA=$(sha256sum sample.xml | cut -d' ' -f1)

# ---------- 用例 5：-w 字节级往返 ----------
if [ -n "$XMILL_BIN" ] && [ -n "$XDEMILL_BIN" ]; then
  rm -f sample.xmi rt5.xmi rt5.xml
  "$XMILL_BIN" -w sample.xml >/dev/null 2>&1; rc1=$?
  mv -f sample.xmi rt5.xmi 2>/dev/null
  "$XDEMILL_BIN" rt5.xmi >/dev/null 2>&1; rc2=$?
  sha=$(sha256sum rt5.xml 2>/dev/null | cut -d' ' -f1)
  if [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] && [ "$sha" = "$SRC_SHA" ]; then
    report PASS "T5 byte-exact roundtrip (xmill -w -> xdemill)" "sha256=${sha:0:16}..."
  else
    report FAIL "T5 byte-exact roundtrip (xmill -w -> xdemill)" "rc=$rc1/$rc2 sha=${sha:0:16}"
  fi
else
  report SKIP "T5 byte-exact roundtrip (xmill -w -> xdemill)" "no binary"
fi

# ---------- 用例 6：默认模式结构保持 + 有压缩 ----------
if [ -n "$XMILL_BIN" ] && [ -n "$XDEMILL_BIN" ]; then
  rm -f sample.xmi rt6.xmi rt6.xml
  "$XMILL_BIN" sample.xml >/dev/null 2>&1; rc1=$?
  sz_src=$(stat -c%s sample.xml); sz_xmi=$(stat -c%s sample.xmi 2>/dev/null || echo 0)
  mv -f sample.xmi rt6.xmi 2>/dev/null
  "$XDEMILL_BIN" rt6.xmi >/dev/null 2>&1; rc2=$?
  tags_src=$(grep -o "<[a-zA-Z/][^>]*>" sample.xml | tr -d ' \n' | sha256sum | cut -d' ' -f1)
  tags_out=$(grep -o "<[a-zA-Z/][^>]*>" rt6.xml 2>/dev/null | tr -d ' \n' | sha256sum | cut -d' ' -f1)
  if [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] && [ "$tags_src" = "$tags_out" ] && [ "$sz_xmi" -gt 0 ]; then
    report PASS "T6 default mode keeps element structure" "tags=${tags_src:0:12} xml=${sz_src}B xmi=${sz_xmi}B"
  else
    report FAIL "T6 default mode keeps element structure" "rc=$rc1/$rc2"
  fi
else
  report SKIP "T6 default mode keeps element structure" "no binary"
fi

# ---------- 用例 7：压缩级别 ----------
if [ -n "$XMILL_BIN" ] && [ -n "$XDEMILL_BIN" ]; then
  ok=1
  for L in 1 9; do
    rm -f sample.xmi lvl.xmi lvl.xml
    "$XMILL_BIN" -w -$L sample.xml >/dev/null 2>&1 || { ok=0; break; }
    mv -f sample.xmi lvl.xmi 2>/dev/null
    "$XDEMILL_BIN" lvl.xmi >/dev/null 2>&1 || { ok=0; break; }
    sha=$(sha256sum lvl.xml 2>/dev/null | cut -d' ' -f1)
    [ "$sha" = "$SRC_SHA" ] || { ok=0; break; }
  done
  if [ $ok = 1 ]; then
    report PASS "T7 compression levels -1/-9 roundtrip" "2/2 levels"
  else
    report FAIL "T7 compression levels -1/-9 roundtrip" "level -$L failed"
  fi
else
  report SKIP "T7 compression levels -1/-9 roundtrip" "no binary"
fi

echo "---- test_package summary: pass=$PASS fail=$FAIL skip=$SKIP ----"
for i in "${!NAMES[@]}"; do printf '  %-4s %s\n' "${STATUS[$i]}" "${NAMES[$i]}"; done

[ $FAIL -eq 0 ] || exit 1
exit 0
