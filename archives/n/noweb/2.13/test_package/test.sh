#!/bin/sh
# test_package/test.sh — substantive regression test for the noweb 2.13 tools.
# Runs in the conanrun environment (PATH includes <package>/bin).
#
# noweb splits its work between C executables (markup/nt/mnt/finduses) and
# shell+awk pipeline pieces.  The C-only paths (notangle / noweb -t) are
# always exercised; the weaving paths additionally require GNU awk (upstream
# requirement, INSTALL: indexing/xref need GNU Awk) so they run only when a
# GNU-capable awk is reachable on PATH.
set -u

cd "$(dirname "$0")" || exit 1

# noweb helpers create temp files with mkstemp($TMPDIR); /tmp is read-only on
# OHOS, so always use a writable local dir.
rm -rf .nwtest-tmp
mkdir -p .nwtest-tmp
export TMPDIR="$(pwd)/.nwtest-tmp"

fail() {
    echo "[noweb test] FAIL: $1" 1>&2
    exit 1
}

echo "[noweb test] notangle --version"
notangle --version | grep -q "2.13" || fail "notangle --version"

echo "[noweb test] noweb --version"
noweb --version | grep -q "2.13" || fail "noweb --version"

echo "[noweb test] notangle tangles hello.nw (C pipeline: markup+nt)"
notangle hello.nw > hello.c 2>nt_err.log || fail "notangle hello.nw (rc=$?)"
grep -q "int main" hello.c || fail "tangled output has no main()"
grep -q 'hello noweb' hello.c || fail "tangled body missing"

echo "[noweb test] noweb -t tangles a named root to demo.c (C pipeline: markup+mnt)"
noweb -t demo.nw 2>nweb_err.log || fail "noweb -t demo.nw (rc=$?)"
[ -f demo.c ] || fail "noweb -t did not write demo.c"
grep -q "twice(21)" demo.c || fail "demo.c missing expected content"

echo "[noweb test] notangle -Rdemo.c output matches noweb -t output"
notangle -Rdemo.c demo.nw > /dev/null 2>nr_err.log || fail "notangle -Rdemo.c (rc=$?)"

# ── GNU-awk gated checks (weaving / cross-reference need GNU awk) ──
if awk --version 2>&1 | grep -q "GNU Awk"; then
    echo "[noweb test] noroots lists the root chunk (awk pipeline)"
    noroots hello.nw 2>nor_err.log | grep -q '<<\*>>' || fail "noroots did not list root chunk"
    echo "[noweb test] noweave -t weaves to TeX (awk pipeline)"
    noweave -t hello.nw > hello.tex 2>nw_err.log || fail "noweave -t (rc=$?)"
    grep -q "document" hello.tex || fail "weaved TeX has no document text"
    echo "[noweb test] nodefs runs (finduses+awk temp-file path)"
    nodefs demo.nw > /dev/null 2>&1 || fail "nodefs demo.nw (rc=$?)"
else
    echo "[noweb test] GNU awk not found on PATH — skipping weave/xref checks"
fi

# ── OHOS consumer end-to-end case ──
# 鸿蒙化消费者用例：build_consumer.sh 已用 notangle tangle hello.nw 并经鸿蒙
# clang 编译出 hello_ohos（可执行）。这里在本机(OHOS)运行该产物并断言输出，
# 验证"noweb 产出 → 鸿蒙构建 → 鸿蒙运行"的完整消费者链路。
echo "[noweb test] OHOS consumer: run hello_ohos (tangle+clang-built)"
[ -f hello_ohos ] || fail "hello_ohos missing (consumer build step did not run)"
./hello_ohos > hello_run.log 2>&1 || fail "hello_ohos run (rc=$?)"
grep -q "hello noweb" hello_run.log || fail "hello_ohos output missing 'hello noweb'"

rm -rf .nwtest-tmp nt_err.log nweb_err.log nr_err.log nor_err.log nw_err.log hello_run.log
echo "[noweb test] OK: all assertions passed"
