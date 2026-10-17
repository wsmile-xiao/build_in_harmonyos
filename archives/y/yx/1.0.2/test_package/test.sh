#!/data/service/hnp/bin/bash
# test_package/test.sh — end-to-end L1 test for the `yx` executable (R34).
# Runs inside the `conanrun` environment, so `yx` resolves to the packaged bin/.
# Every check executes the real binary and asserts its output / exit status.
set -eu

echo "[test] yx --version"
yx --version | grep -q "1.0.2"

echo "[test] list all mapping keys (implicit stdin)"
out="$(printf 'foo: one\nbar: two\nblah: argh\n' | yx)"
[ "$out" = "$(printf 'foo\nbar\nblah')" ]

echo "[test] extract a nested scalar by path (explicit stdin)"
out="$(printf 'foo:\n  bar:\n    blah: three\n' | yx -f - foo bar blah)"
[ "$out" = "three" ]

echo "[test] list all sequence indices"
out="$(printf -- '- one\n- two\n- three\n' | yx)"
[ "$out" = "$(printf '1\n2\n3')" ]

echo "[test] extract a sequence index to scalar"
out="$(printf -- '- one\n- two\n- three\n' | yx 2)"
[ "$out" = "two" ]

echo "[test] unknown key must exit non-zero"
if printf 'foo: one\n' | yx nope >/dev/null 2>&1; then
    echo "FAIL: unknown key should have returned non-zero" >&2
    exit 1
fi

echo "test_package: yx OK"
