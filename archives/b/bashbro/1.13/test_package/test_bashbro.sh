#!/bin/sh
# test_package/test_bashbro.sh
# Verifies bashbro package content is installed correctly.
#
# CI worker sandbox PATH does not contain `bash` (bash lives in
# /data/service/hnp/bin/bash). This script is invoked via
# self.run('bash test_bashbro.sh ...', env="conanrun"), so conanrun.sh
# sets PATH to include /data/service/hnp/bin. All `bash` calls below
# rely on that PATH — do not hardcode an absolute bash path.
set -e

BC_ROOT="${1:-}"

if [ -z "$BC_ROOT" ]; then
    echo "Usage: $0 <package_root>"
    exit 1
fi

LAUNCHER="$BC_ROOT/bin/bashbro"
MAN_PAGE="$BC_ROOT/share/man/man1/bashbro.1"
LICENSE="$BC_ROOT/share/bashbro/LICENSE"

# 1. Main script exists
if [ ! -f "$LAUNCHER" ]; then
    echo "FAIL: bashbro script not found at $LAUNCHER"
    exit 1
fi

# 2. Man page exists
if [ ! -f "$MAN_PAGE" ]; then
    echo "FAIL: man page not found at $MAN_PAGE"
    exit 1
fi

# 3. LICENSE exists
if [ ! -f "$LICENSE" ]; then
    echo "FAIL: LICENSE not found at $LICENSE"
    exit 1
fi

# 4. R34 实质校验: bash -n 语法检查主脚本
bash -n "$LAUNCHER"

# 5. R34 实质校验: 验证脚本内 VERSION 字符串
#    不执行 bashbro --version：它先做依赖检查（socat/tree/sed），
#    缺失就 exit 1。改为 grep 脚本内的 VERSION 声明。
grep -q "declare -r VERSION=1.13" "$LAUNCHER"

echo "PASS: bashbro package verified (script + man page + LICENSE, version OK)"
