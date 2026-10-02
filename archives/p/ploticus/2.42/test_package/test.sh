#!/data/service/hnp/bin/bash
# test_package/test.sh — ploticus 2.42 L1 消费者测试
#
# 通过**实际运行被测二进制**（bin/pl）与**实际链接被测静态库**
# （lib/libploticus.a）完成验证（R34）。逐用例打印 PASS/FAIL，末尾汇总，
# 任一用例失败 -> exit 1。
#
# 用法: test.sh <pl-binary> <package-folder> [work-dir] [c-compiler]
set -u

PL="${1:?usage: test.sh <pl-binary> <package-folder> [work-dir] [c-compiler]}"
PKG="${2:?usage: test.sh <pl-binary> <package-folder> [work-dir] [c-compiler]}"
WORK_DIR="${3:-}"
CC_BIN="${4:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "$WORK_DIR" ]; then
  WORK="$WORK_DIR"
else
  WORK="$SCRIPT_DIR/ploticus_l1_work"
fi
rm -rf "$WORK"; mkdir -p "$WORK"
cd "$WORK" || exit 1
cp "$SCRIPT_DIR/ohos_l1_probe.pl" . || exit 1

total=0; passed=0; failed=0; skipped=0

ok()    { total=$((total+1)); passed=$((passed+1)); echo "[PASS ] $1"; }
bad()   { total=$((total+1)); failed=$((failed+1)); echo "[FAIL ] $1 -> $2"; }
skip()  { total=$((total+1)); skipped=$((skipped+1)); echo "[SKIP ] $1 -> $2"; }

# 真正的错误行 = "error NNN:" 且不含 warning
real_errors() { grep -E "error [0-9]+:" "$1" 2>/dev/null | grep -vi warning | wc -l | tr -d ' '; }

echo "== ploticus 2.42 L1 test =="
echo "pl  : $PL"
echo "pkg : $PKG"
echo "work: $WORK"
echo

# ---------------------------------------------------------------- case 1
# 注：上游 `pl -version` 打印横幅后以 1 退出（未给出脚本文件），属上游行为，
# 因此本用例只校验横幅内容，不要求 rc=0。
"$PL" -version >version.txt 2>&1
rc=$?
if grep -q "ploticus 2.42" version.txt && grep -q "PNG" version.txt; then
  ok "version_banner (横幅含 'ploticus 2.42' 与 'PNG'; upstream rc=$rc)"
else
  bad "version_banner" "rc=$rc, version.txt: $(head -1 version.txt)"
fi


# ---------------------------------------------------------------- case 2
rm -f ohos_l1_probe.png
"$PL" -png ohos_l1_probe.pl >png.txt 2>&1
rc=$?
magic=""
[ -f ohos_l1_probe.png ] && magic="$(od -An -tx1 -N8 ohos_l1_probe.png | tr -d ' \n')"
if [ "$rc" -eq 0 ] && [ "$magic" = "89504e470d0a1a0a" ] && [ "$(real_errors png.txt)" -eq 0 ]; then
  wh="$(od -An -tx1 -j16 -N8 ohos_l1_probe.png | tr -d ' \n')"
  w=$((16#${wh:0:8})); h=$((16#${wh:8:8}))
  if [ "$w" -gt 0 ] && [ "$h" -gt 0 ]; then
    ok "png_render (PNG 魔数正确; IHDR=${w}x${h}; 无 error 行)"
  else
    bad "png_render" "IHDR 尺寸异常 ${w}x${h}"
  fi
else
  bad "png_render" "rc=$rc magic=$magic errors=$(real_errors png.txt)"
fi

# ---------------------------------------------------------------- case 3
rm -f ohos_l1_probe.svg
"$PL" -svg ohos_l1_probe.pl >svg.txt 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s ohos_l1_probe.svg ] && grep -qi "<svg" ohos_l1_probe.svg \
   && [ "$(real_errors svg.txt)" -eq 0 ]; then
  ok "svg_render (SVG 已生成且含 <svg>; 无 error 行)"
else
  bad "svg_render" "rc=$rc size=$(stat -c%s ohos_l1_probe.svg 2>/dev/null || echo none)"
fi

# ---------------------------------------------------------------- case 4  【鸿蒙特有】
# 鸿蒙 PC 将 /tmp 挂载为只读。把 TMPDIR 指向该只读目录，验证 proc drawcommands
# 的临时文件不会因此丢失（适配补丁 0001 的运行时目录选择）。
mkdir -p ohos_tmp && cp ohos_l1_probe.pl ohos_tmp/ && cd ohos_tmp
rm -f ohos_l1_probe.png
TMPDIR=/tmp "$PL" -png ohos_l1_probe.pl >tmpdir.txt 2>&1
rc=$?
if grep -q "Cannot open draw commands file" tmpdir.txt; then
  bad "ohos_tmpdir_readonly" "TMPDIR=/tmp(只读) 时临时文件仍失败: $(grep -m1 'error' tmpdir.txt)"
elif [ "$rc" -eq 0 ] && [ -s ohos_l1_probe.png ] && [ "$(real_errors tmpdir.txt)" -eq 0 ]; then
  ok "ohos_tmpdir_readonly (TMPDIR 为只读时仍渲染成功, 无 error 行)"
else
  bad "ohos_tmpdir_readonly" "rc=$rc size=$(stat -c%s ohos_l1_probe.png 2>/dev/null || echo none) errors=$(real_errors tmpdir.txt)"
fi
cd "$WORK"

# ---------------------------------------------------------------- case 5  【鸿蒙特有】
elf_magic="$(od -An -tx1 -N4 "$PL" | tr -d ' \n')"
elf_class="$(od -An -tx1 -j4 -N1 "$PL" | tr -d ' \n')"
elf_mach="$(od -An -tx1 -j18 -N2 "$PL" | tr -d ' \n')"
if [ "$elf_magic" = "7f454c46" ] && [ "$elf_class" = "02" ] && [ "$elf_mach" = "b700" ]; then
  # zlib 是系统同名库 -> 必须静态链接（不应出现 libz.so 运行时依赖）
  if grep -q "libz\.so" "$PL"; then
    bad "ohos_elf_abi" "存在 libz.so 动态依赖（R26 要求系统同名库静态链接）"
  else
    ok "ohos_elf_abi (ELF64 + EM_AARCH64(0xb7); 无 libz.so 动态依赖)"
  fi
else
  bad "ohos_elf_abi" "magic=$elf_magic class=$elf_class machine=$elf_mach"
fi

# ---------------------------------------------------------------- case 6  【鸿蒙特有】
# PLOTICUS_PREFABS 由 recipe 的 runenv_info 提供（conanrun 环境）
pref="${PLOTICUS_PREFABS:-}"
if [ ! -d "$pref" ] || [ ! -f "$pref/vbars.pl" ]; then
  bad "ohos_prefab_render" "PLOTICUS_PREFABS 未指向包内 prefabs: '$pref'"
else
  printf 'Jan 10\nFeb 20\nMar 15\n' >prefab_data
  rm -f prefab.png
  "$PL" -prefab vbars data=prefab_data x=1 y=2 -png -o prefab.png >prefab.txt 2>&1
  rc=$?
  pmagic=""
  [ -f prefab.png ] && pmagic="$(od -An -tx1 -N8 prefab.png | tr -d ' \n')"
  if [ "$rc" -eq 0 ] && [ "$pmagic" = "89504e470d0a1a0a" ]; then
    ok "ohos_prefab_render (包内 prefabs 渲染成功: $(stat -c%s prefab.png) 字节)"
  else
    bad "ohos_prefab_render" "rc=$rc magic=$pmagic: $(tail -2 prefab.txt | tr '\n' ' ')"
  fi
fi

# ---------------------------------------------------------------- case 7
if [ -z "$CC_BIN" ]; then
  for c in clang /data/service/hnp/bin/clang cc gcc; do
    if command -v "$c" >/dev/null 2>&1; then CC_BIN="$c"; break; fi
  done
fi
if [ -z "$CC_BIN" ]; then
  skip "libploticus_api" "测试环境无可用 C 编译器"
else
  cat >api_probe.c <<'EOF'
/* L1: 使用包内 libploticus.a + libploticus.h 的嵌入 API
 *
 * 注意：libploticus 的 ploticus_init()/ploticus_execline() 会**就地修改**传入的
 * 字符串（按脚本语言解析），因此必须传可写缓冲区；传字符串字面量会 SIGSEGV。
 * 这里完全照搬上游 apitest.c 的调用序列（init -> arg -> execscript -> end ->
 * init -> arg -> execline* -> end）。
 */
#include <stdio.h>
#include <string.h>

extern int ploticus_init( char *device, char *outfilename );
extern int ploticus_arg( char *name, char *value );
extern int ploticus_execscript( char *scriptfile, int prefabflag );
extern int ploticus_execline( char *line );
extern int ploticus_end();

int main( int argc, char **argv )
{
    char device[16], outfile[80], buf[256];
    int rc;

    if( argc < 2 ) { fprintf( stderr, "usage: api_probe <scriptfile>\n" ); return 2; }

    strcpy( device, "png" ); sprintf( outfile, "api_probe1.%s", device );
    rc = ploticus_init( device, outfile );
    if( rc ) { fprintf( stderr, "ploticus_init rc=%d\n", rc ); return 1; }
    rc = ploticus_arg( "-debug", "" );
    if( rc ) { fprintf( stderr, "ploticus_arg rc=%d\n", rc ); return 1; }
    rc = ploticus_execscript( argv[1], 0 );
    if( rc ) { fprintf( stderr, "ploticus_execscript rc=%d\n", rc ); return 1; }
    rc = ploticus_end();
    if( rc ) { fprintf( stderr, "ploticus_end rc=%d\n", rc ); return 1; }

    strcpy( device, "png" ); sprintf( outfile, "api_probe2.%s", device );
    rc = ploticus_init( device, outfile );
    if( rc ) { fprintf( stderr, "ploticus_init(2) rc=%d\n", rc ); return 1; }
    rc = ploticus_arg( "-debug", "" );
    if( rc ) { fprintf( stderr, "ploticus_arg(2) rc=%d\n", rc ); return 1; }
    strcpy( buf, "#proc annotate" );  rc = ploticus_execline( buf );
    if( rc ) { fprintf( stderr, "ploticus_execline rc=%d\n", rc ); return 1; }
    strcpy( buf, "location: 1 1" );   ploticus_execline( buf );
    strcpy( buf, "text: libploticus on HarmonyOS PC" ); ploticus_execline( buf );
    rc = ploticus_end();
    if( rc ) { fprintf( stderr, "ploticus_end(2) rc=%d\n", rc ); return 1; }

    printf( "libploticus API ok\n" );
    return 0;
}
EOF
  # 依赖库（libpng/zlib）的库目录来自 conanrun 的 LD_LIBRARY_PATH
  export LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
  rm -f api_probe api_probe1.png api_probe2.png
  "$CC_BIN" -I"$PKG/include" api_probe.c "$PKG/lib/libploticus.a" \
      -lpng -lz -lm -o api_probe >api_build.txt 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    bad "libploticus_api" "编译失败: $(tail -2 api_build.txt | tr '\n' ' ')"
  else
    ./api_probe ohos_l1_probe.pl >api_run.txt 2>&1
    rc=$?
    m1=""; m2=""
    [ -f api_probe1.png ] && m1="$(od -An -tx1 -N8 api_probe1.png | tr -d ' \n')"
    [ -f api_probe2.png ] && m2="$(od -An -tx1 -N8 api_probe2.png | tr -d ' \n')"
    if [ "$rc" -eq 0 ] && [ "$m1" = "89504e470d0a1a0a" ] && [ "$m2" = "89504e470d0a1a0a" ]; then
      ok "libploticus_api (链接包内静态库, 脚本+内嵌脚本两种方式出图各 1 张)"
    else
      bad "libploticus_api" "运行失败 rc=$rc m1=$m1 m2=$m2: $(tail -2 api_run.txt | tr '\n' ' ')"
    fi
  fi
fi

echo
echo "== 汇总: 用例 $total / 通过 $passed / 失败 $failed / 跳过 $skipped =="
[ "$failed" -eq 0 ] || exit 1
exit 0
