#!/bin/sh
# intercal 0.30 消费者测试（真实产品路径：ick → C → 原生 ELF → 运行 → 断言输出）
#
# 本文件同时是 CI 门禁 L0c 要求的"测试源文件"（`ci/conan/build_and_test.sh` L0c：
# test_package/ 下必须存在 *.c/*.cpp/*.cc/*.cxx/*.sh/*.py 之一，且显式排除 conanfile.py）。
# 原先全部断言都写在 conanfile.py 的 test() 里 ⇒ 该目录里唯一的测试资产是 `hello.i`
# （INTERCAL 源码，不在 L0c 认可的后缀清单内）⇒ CI 判 `no_test_sources`。
# 断言本身不因搬迁而减弱：三条检查逐条可失败，任一失败即非零退出。
#
# 由 test_package/conanfile.py 的 test() 以 `sh smoke.sh` 调起（HMDFS 上脚本可能无执行位，
# 故不依赖 shebang 生效），环境变量：ICK / CC / SRC / WORK / BINDIR。
set -u

pass=0
fail=0
ok()   { echo "ok - $1"; pass=$((pass + 1)); }
bad()  { echo "NOT OK - $1"; fail=$((fail + 1)); }
die()  { echo "NOT OK - $1"; echo "CONSUMER_RESULT 0/1 (fatal)"; exit 1; }

for var in ICK CC SRC WORK BINDIR; do
    eval "val=\${$var:-}"
    [ -n "$val" ] || die "required env var $var is empty"
done
[ -f "$ICK" ] || die "installed ick binary not found at $ICK"
[ -f "$SRC" ] || die "INTERCAL source asset not found at $SRC"

mkdir -p "$WORK" || die "cannot create work dir $WORK"
cd "$WORK" || die "cannot cd to $WORK"
export PATH="$BINDIR:$PATH"
export CC="$CC"

# 断言 ①：ick 必须真的把 INTERCAL 源码编成同名原生可执行文件（退出码 0 + 产物存在）
if "$ICK" -b hello.i > ick.log 2>&1; then
    if [ -f "$WORK/hello" ]; then
        ok "ick -b hello.i exited 0 and produced ./hello"
    else
        tail -20 ick.log
        bad "ick exited 0 but produced no ./hello"
    fi
else
    rc=$?
    tail -20 ick.log
    bad "ick -b hello.i failed (rc=$rc)"
fi

# 断言 ②：产物必须是本机的 ELF 原生二进制（证明 ick 走完了 C 编译+链接，不是脚本或桩）
if [ -f "$WORK/hello" ]; then
    magic=$(od -An -tx1 -N4 "$WORK/hello" | tr -d ' \n')
    if [ "$magic" = "7f454c46" ]; then
        ok "./hello is an ELF image (magic=$magic)"
    else
        bad "./hello is not ELF (first 4 bytes=$magic)"
    fi
else
    bad "skipped ELF check: ./hello absent"
fi

# 断言 ③：运行产物、断言它打印 hello, world（运行期行为，不是查文件存在）
if [ -f "$WORK/hello" ]; then
    if ./hello > hello.out 2>&1; then
        if grep -q "hello, world" hello.out; then
            ok "compiled program printed 'hello, world' ($(wc -c < hello.out) bytes on stdout)"
        else
            echo "   stdout was: $(head -c 200 hello.out)"
            bad "program exited 0 but did not print 'hello, world'"
        fi
    else
        rc=$?
        echo "   stdout/stderr was: $(head -c 200 hello.out)"
        bad "compiled program exited $rc"
    fi
else
    bad "skipped run check: ./hello absent"
fi

echo "CONSUMER_RESULT $pass/$((pass + fail)) (failures=$fail)"
[ "$fail" -eq 0 ] || exit 1
exit 0
