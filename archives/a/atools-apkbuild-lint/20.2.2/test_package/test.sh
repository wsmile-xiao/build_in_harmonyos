#!/bin/sh
# test_package/test.sh — atools-apkbuild-lint 消费者功能测试
# 运行于 conanrun 环境（PATH 已包含安装后的 bin/）；由 conanfile.test() 以
# CONFIG_SHELL（缺省 /bin/sh）显式解释执行，脚本本体为 POSIX sh
# 四个真实用例（对安装后的 apkbuild-lint 脚本执行真实 lint）:
#   TC1: apkbuild-lint 存在且可执行
#   TC2: 干净 APKBUILD（pkgname=a/pkgver=1，上游 'mesa good version' 同形）→ 退出码 0 且无任何告警输出
#   TC3: builddir 为默认值 → 退出码 1，首行含 [AL1] 标签（与上游
#        tests/apkbuild-lint.bats 'default builddir can be removed' 断言一致）
#   TC4: pkgver=21.0.0 触发坏版本正则 → 退出码 1，输出含 [AL61]
set -u

discovered=4
passed=0
failed=0

# 临时目录链与配方/bats-shim 一致（HMBS 注入的 TMPDIR/TMP/TEMP 优先）；
# 真机 /tmp 只读，mktemp -d 不带模板会默认写 /tmp，必须显式指定可写目录
tb="${TMPDIR:-${TMP:-${TEMP:-}}}"
tb="${tb%/}"
work=""
if [ -n "$tb" ] && command -v mktemp >/dev/null 2>&1; then
    work="$(mktemp -d "$tb/atools-lint-testpkg.XXXXXXXX" 2>/dev/null)" || work=""
fi
if [ -z "$work" ]; then
    # 兜底：落在当前目录（conan test_package 构建目录，必可写）
    work="./atools-lint-testpkg.$"
    (umask 077 && mkdir "$work") || exit 3
fi
trap 'rm -rf "$work"' EXIT

lint="$(command -v apkbuild-lint 2>/dev/null)"

# TC1 二进制存在且可执行
if [ -n "$lint" ] && [ -x "$lint" ]; then
    passed=$((passed + 1))
    echo "[ok] TC1: apkbuild-lint present and executable ($lint)"
else
    failed=$((failed + 1))
    echo "[fail] TC1: apkbuild-lint missing from PATH or not executable"
fi

fixture="$work/APKBUILD"

# TC2 干净 APKBUILD → rc=0、无输出
printf 'pkgname=mesa\npkgver=21.0.1\n' > "$fixture"
out="$(apkbuild-lint "$fixture" 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && [ -z "$out" ]; then
    passed=$((passed + 1))
    echo "[ok] TC2: clean APKBUILD passes silently (rc=0, no output)"
else
    failed=$((failed + 1))
    echo "[fail] TC2: clean APKBUILD unexpected (rc=$rc, output: $out)"
fi

# TC3 默认 builddir → rc=1 + [AL1]
# 注意先捕获完整输出与 linter 退出码，再取首行；若写成
# `out | head -n 1` 后取 $?, 拿到的是 head 的退出码
printf 'pkgname=a\npkgver=1\nbuilddir=/$pkgname-$pkgver\n\nbuild() {\n\tfoo\n}\n' > "$fixture"
out="$(apkbuild-lint "$fixture" 2>&1)"
rc=$?
first="$(printf '%s\n' "$out" | head -n 1)"
if [ "$rc" -eq 1 ] && printf '%s' "$first" | grep -qE '\[AL1\].*:builddir can be removed as it is the default value'; then
    passed=$((passed + 1))
    echo "[ok] TC3: default builddir flagged ([AL1], rc=1)"
else
    failed=$((failed + 1))
    echo "[fail] TC3: default builddir case unexpected (rc=$rc, first line: $first)"
fi

# TC4 坏版本正则 → rc=1 + [AL61]
printf 'pkgname=mesa\npkgver=21.0.0\n' > "$fixture"
out="$(apkbuild-lint "$fixture" 2>&1)"
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qE '\[AL61\].*:Version .21\.0.0. matches a bad version regex'; then
    passed=$((passed + 1))
    echo "[ok] TC4: bad version regex flagged ([AL61], rc=1)"
else
    failed=$((failed + 1))
    echo "[fail] TC4: bad version case unexpected (rc=$rc, output: $out)"
fi

if [ $failed -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 1
fi
