#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for oksh executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] oksh -c 'echo hello'"
out=$(oksh -c 'echo hello')
if [ "$out" = "hello" ]; then
    echo "  ok: echo hello"
else
    echo "  fail: expected 'hello', got '$out'"
    exit 1
fi

echo "[test] oksh -c 'x=5; y=3; echo \$((x+y))'"
out=$(oksh -c 'x=5; y=3; echo $((x+y))')
if [ "$out" = "8" ]; then
    echo "  ok: arithmetic expansion"
else
    echo "  fail: expected '8', got '$out'"
    exit 1
fi

echo "[test] oksh -c 's=hello; echo \${s%lo}'"
out=$(oksh -c 's=hello; echo ${s%lo}')
if [ "$out" = "hel" ]; then
    echo "  ok: parameter substitution"
else
    echo "  fail: expected 'hel', got '$out'"
    exit 1
fi

echo "[test] oksh -c 'for i in a b c; do echo \$i; done'"
out=$(oksh -c 'for i in a b c; do echo $i; done' | tr '\n' ' ')
if [ "$out" = "a b c " ]; then
    echo "  ok: for loop"
else
    echo "  fail: expected 'a b c ', got '$out'"
    exit 1
fi

echo "[test] oksh -c 'echo \$KSH_VERSION'"
oksh -c 'echo $KSH_VERSION' && echo "  ok: KSH_VERSION accessible" || {
    echo "  fail: KSH_VERSION not accessible"
    exit 1
}

echo "[test] oksh -c 'if [ 1 -lt 2 ]; then echo yes; fi'"
out=$(oksh -c 'if [ 1 -lt 2 ]; then echo yes; fi')
if [ "$out" = "yes" ]; then
    echo "  ok: conditional test"
else
    echo "  fail: expected 'yes', got '$out'"
    exit 1
fi

echo "✅ all tests passed"
