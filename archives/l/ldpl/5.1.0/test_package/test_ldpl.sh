#!/bin/sh
# Consumer test for ldpl 5.1.0 on HarmonyOS PC (OHOS aarch64).
#
# LDPL is a transpiler: it emits C++ and then shells out to a C++ front-end.
# Upstream 5.1.0 hard-codes both the library directory (baked in at build time)
# and the front-end name "c++". On OHOS neither holds: there is no "c++"/"g++"
# on PATH, only the SDK's clang++, and a downloaded package cannot rely on the
# build-machine path. So every case below drives the installed binary through
# the two run-time overrides the patch adds, which is exactly the behaviour a
# HarmonyOS consumer needs.
#
#   usage: sh test_ldpl.sh <path to installed ldpl> <path to samples dir>
#   env  : LDPL_CXX            C++ front-end used by ldpl (required here)
#          LDPL_LIB_LOCATION   dir holding ldpl_lib.cpp / BigInt.hpp (from conanrun)

LDPL="$1"
SAMPLES="$2"
PASS=0
FAIL=0

ok()  { PASS=$((PASS+1)); echo "  ok   - $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL - $1"; }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else bad "$2 (rc=$1)"; fi; }

if [ ! -x "$LDPL" ]; then
    echo "ldpl binary not found or not executable: $LDPL" >&2
    exit 1
fi
if [ ! -d "$SAMPLES" ]; then
    echo "samples dir not found: $SAMPLES" >&2
    exit 1
fi

WORK="${TMPDIR:-$PWD}/ldpl-consumer-$$"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 1
cd "$WORK" || exit 1

# ldpl 用「源码路径截到第一个点为止 + -bin」推导产物名，传绝对路径就会把可执行文件
# 写到源码所在的目录去。所以样例一律复制进工作目录、用相对文件名调用。
cp "$SAMPLES"/*.ldpl "$WORK"/ || exit 1

echo "  ldpl    : $LDPL"
echo "  LDPL_CXX: ${LDPL_CXX:-<unset>}"
echo "  LDPL_LIB_LOCATION: ${LDPL_LIB_LOCATION:-<unset>}"
echo

# ldpl 5.1.0 appends -static-libgcc -static-libstdc++ unless -n is given; the OHOS
# SDK ships libc++ only, so honour upstream's own switch when the binary offers it.
NONSTATIC=""
"$LDPL" -h >"$WORK/help.out" 2>&1
grep -q 'non-static' "$WORK/help.out" && NONSTATIC="-n"
echo "  static-libc++ flags off via: ${NONSTATIC:-<not offered by this build>}"
echo

# --- 1) 二进制就位 -----------------------------------------------------------
[ -x "$LDPL" ]; chk $? "[1] installed ldpl is executable"

# --- 2) -v：版本与代号 --------------------------------------------------------
"$LDPL" -v >"$WORK/v.out" 2>&1
chk $? "[2] ldpl -v exits 0"
grep -q 'LDPL version 5.1.0' "$WORK/v.out"
chk $? "[3] -v reports version 5.1.0 (matches the tag)"
grep -q "Groovy Gualicho" "$WORK/v.out"
chk $? "[4] -v reports the 5.1.0 codename 'Groovy Gualicho'"

# --- 3) -h / 未知选项 ---------------------------------------------------------
grep -q 'Usage' "$WORK/help.out"
chk $? "[5] -h prints the usage block"
"$LDPL" --definitely-not-an-option >"$WORK/unknown.out" 2>&1
grep -q 'Unknown option' "$WORK/unknown.out"
chk $? "[6] unknown option is reported, not silently accepted"

# --- 4) 运行期资源定位（补丁核心）--------------------------------------------
[ -n "${LDPL_LIB_LOCATION:-}" ]
chk $? "[7] LDPL_LIB_LOCATION is injected by the package runenv"
"$LDPL" -r "hello.ldpl" >"$WORK/ir.out" 2>&1
grep -q "#include \"$LDPL_LIB_LOCATION/ldpl_lib.cpp\"" "$WORK/ir.out"
chk $? "[8] generated C++ includes ldpl_lib.cpp from the run-time path, not the baked one"

# --- 5) 端到端：编译 + 运行 --------------------------------------------------
compile_run() {  # $1=sample basename  $2=expected file  $3=label
  src="$1.ldpl"
  "$LDPL" $NONSTATIC -f=-pthread "$src" >"$WORK/$1.build.out" 2>&1
  if [ $? -ne 0 ]; then
    sed -n '1,20p' "$WORK/$1.build.out"
    bad "[$3] $1.ldpl compiles"
    return 1
  fi
  ok "[$3] $1.ldpl compiles"
  "./$1-bin" >"$WORK/$1.run.out" 2>&1
  return 0
}

compile_run hello expect-hello 9
if [ -x "./hello-bin" ]; then
  printf 'Hello LDPL on HarmonyOS\n' >"$WORK/expect-hello"
  cmp -s "$WORK/hello.run.out" "$WORK/expect-hello"
  chk $? "[10] hello-bin prints exactly 'Hello LDPL on HarmonyOS'"
else
  bad "[10] hello-bin was not produced"
fi

compile_run arithmetic x 11
if [ -x "./arithmetic-bin" ]; then
  grep -q '^12$' "$WORK/arithmetic.run.out"
  chk $? "[12] IN _ SOLVE _ evaluates 3*(2*2) to 12"
else
  bad "[12] arithmetic-bin was not produced"
fi

compile_run collections x 13
if [ -x "./collections-bin" ]; then
  grep -q '^12$' "$WORK/collections.run.out"
  chk $? "[14] number map keys sum (myMap:1 + myMap:2) to 12"
else
  bad "[14] collections-bin was not produced"
fi

compile_run subproc x 15
if [ -x "./subproc-bin" ]; then
  grep -q 'hi from subprocedure' "$WORK/subproc.run.out"
  chk $? "[16] SUB-PROCEDURE / CALL / RETURN runs"
  grep -q '^3$' "$WORK/subproc.run.out"
  chk $? "[17] global DATA survives the sub-procedure call"
else
  bad "[17] subproc-bin was not produced"
fi

# --- 6) 标准输入：ACCEPT ------------------------------------------------------
"$LDPL" $NONSTATIC -f=-pthread "accept.ldpl" >"$WORK/accept.build.out" 2>&1
chk $? "[18] accept.ldpl compiles"
printf 'OscarP\n' | ./accept-bin >"$WORK/accept.run.out" 2>&1
grep -q 'got\[OscarP\]' "$WORK/accept.run.out"
chk $? "[19] ACCEPT reads stdin inside the generated program"

# --- 7) -o= 指定产物名 --------------------------------------------------------
"$LDPL" $NONSTATIC -f=-pthread -o=custom-name "hello.ldpl" >"$WORK/o.out" 2>&1
chk $? "[20] -o=custom-name compiles"
[ -x "./custom-name" ] && ./custom-name >"$WORK/custom.run.out" 2>&1
cmp -s "$WORK/custom.run.out" "$WORK/expect-hello"
chk $? "[21] -o= honours the requested output name and still runs"

# --- 8) 负向：语法错误必须让编译器失败 --------------------------------------
"$LDPL" $NONSTATIC -f=-pthread "bad.ldpl" >"$WORK/bad.out" 2>&1
rc=$?
[ "$rc" -ne 0 ]
chk $? "[22] a malformed .ldpl does not exit 0 (rc=$rc)"
grep -q 'LDPL Error' "$WORK/bad.out"
chk $? "[23] the malformed source reports 'LDPL Error'"

# --- 9) 重定位反证：换一个 lib 目录照样能用 ----------------------------------
ALT="$WORK/altlib"
if [ -n "${LDPL_LIB_LOCATION:-}" ] && [ -f "$LDPL_LIB_LOCATION/ldpl_lib.cpp" ]; then
  mkdir -p "$ALT"
  cp "$LDPL_LIB_LOCATION/ldpl_lib.cpp" "$ALT/"
  cp "$LDPL_LIB_LOCATION/BigInt.hpp" "$ALT/" 2>/dev/null
  ( LDPL_LIB_LOCATION="$ALT" "$LDPL" $NONSTATIC -f=-pthread -o=relocated "hello.ldpl" ) \
      >"$WORK/reloc.out" 2>&1
  chk $? "[24] ldpl works with LDPL_LIB_LOCATION pointed at a relocated copy"
  ./relocated >"$WORK/reloc.run.out" 2>&1
  cmp -s "$WORK/reloc.run.out" "$WORK/expect-hello"
  chk $? "[25] the relocated build produces the same running program"
else
  bad "[24] ldpl_lib.cpp not found under LDPL_LIB_LOCATION"
  bad "[25] skipped because [24] failed"
fi

# --- 10) 产物是独立的 ELF，不依赖 ldpl --------------------------------------
MAGIC=$(head -c 4 ./hello-bin 2>/dev/null | od -An -c 2>/dev/null | tr -d ' \n')
[ "$MAGIC" = "177ELF" ]
chk $? "[26] hello-bin is a real ELF image (magic 177 E L F, got: ${MAGIC:-none})"

rm -rf "$WORK"
echo
echo "ldpl consumer test: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
