#!/bin/sh
# test_package test.sh — redo-c 0.3 消费者测试
# 使用已安装的 redo 可执行文件驱动真实 .do 构建流程（R34：必须实际调用被测包二进制）。
# redo 二进制通过 conanrun 环境（VirtualRunEnv）注入 PATH。
set -u

redo="${1:-}"
if [ -z "$redo" ]; then
    redo=$(command -v redo 2>/dev/null || true)
fi
if [ -z "$redo" ]; then
    echo "usage: $0 <path-to-redo-binary>  (或通过 conanrun 环境注入 PATH)"
    exit 2
fi
[ -f "$redo" ] || { echo "FAIL: redo not found: $redo"; exit 2; }

BINDIR=$(dirname "$redo")
WD=$(mktemp -d "${TMPDIR:-/tmp}/redo-c-tp-XXXXXX")
trap 'rm -rf "$WD"' EXIT

# redo 内部按 program 名分派（redo-ifchange/redo-ifcreate/...），需在 PATH
PATH="$BINDIR:$PATH" export PATH

printf '#!/bin/sh\nprintf "hello-from-redo-c\\n" > $3\n' > "$WD/hello.do"
chmod 755 "$WD/hello.do"

( cd "$WD" && "$redo" hello ) >/dev/null 2>&1
rc=$?
[ "$rc" = 0 ] || { echo "FAIL: redo exit=$rc"; exit 1; }
[ -f "$WD/hello" ] || { echo "FAIL: target file not produced"; exit 1; }

content=$(cat "$WD/hello")
if [ "$content" != "hello-from-redo-c" ]; then
    echo "FAIL: unexpected content: $content"
    exit 1
fi

echo "redo-c consumer test PASSED: redo built target and produced expected content"
exit 0