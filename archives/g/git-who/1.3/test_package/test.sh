#!/usr/bin/env sh
# test_package/test.sh — 真实调用 git-who 二进制的消费者测试
# 运行于 conanrun env（PATH 含已安装的 bin/），由 test_package/conanfile.py 调用：
#   sh test.sh <path-to-git-who>
#
# 3 个真实用例：
#   1. git-who --version 输出含 "1.3"（版本注入验证）
#   2. git-who --help 输出含 "Usage: git-who"（CLI 入口验证）
#   3. 功能用例：临时 git 仓库内运行 `git-who table`，输出含提交作者名
#      （真实调用 git-who 核心统计逻辑，非空壳）
#
# 每个用例独立计数，结束后输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记
# （discovered/passedCount 来自实际用例计数）。任一失败则退出码 1，
# conan test_package 阶段失败，避免静默通过。
set -u

# HMBS 注入 TMPDIR/TMP/TEMP；先切到可写目录（OHOS /tmp 只读）
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

# OHOS 真机 HMFS 的目录属主上报与进程 euid 不一致，git 的 dubious ownership
# 检查（CVE-2022-24765 防护）会把 TMPDIR 下新建的临时仓库误判为不可信仓库，
# git-who 内部 fork 的 git 子进程因此直接 exit 128。通过环境变量注入
# safe.directory=* 关闭该检查（仅作用于本脚本及其子进程，不改上游代码与测试
# 语义）。GIT_CONFIG_COUNT 系列环境配置与 GIT_CONFIG_GLOBAL/SYSTEM 相互独立，
# git-who 子进程继承本环境后同样生效。
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0='*'

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-git-who>" >&2
    exit 2
fi

git_who_bin="$1"
PASS=0
FAIL=0

if [ ! -f "$git_who_bin" ]; then
    echo "git-who binary not found: $git_who_bin" >&2
    exit 1
fi

# ── 用例 1: --version ──
echo "[case 1/3] git-who --version"
version_output="$("$git_who_bin" --version 2>&1)"
echo "  output: $version_output"
if printf '%s\n' "$version_output" | grep -F "1.3" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] version contains 1.3"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] version output does not contain 1.3"
fi

# ── 用例 2: --help ──
echo "[case 2/3] git-who --help"
help_output="$("$git_who_bin" --help 2>&1)"
if printf '%s\n' "$help_output" | grep -F "Usage: git-who" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] help shows usage"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] help output unexpected: $help_output"
fi

# ── 用例 3: 功能用例 — 临时 git 仓库上运行 git-who table ──
echo "[case 3/3] functional: git-who table on a temp repo"
if command -v git >/dev/null 2>&1; then
    repo_dir="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/git-who-test-$$"
    rm -rf "$repo_dir"
    if git init -q "$repo_dir" 2>/dev/null; then
        if (
            cd "$repo_dir" || exit 1
            git config user.name "Test Author"
            git config user.email "test@example.com"
            printf 'hello\n' > hello.txt
            git add hello.txt
            git commit -qm "init"
        ); then
            table_output="$(
                cd "$repo_dir" 2>/dev/null &&
                GIT_WHO_DISABLE_CACHE=1 GIT_CONFIG_GLOBAL= GIT_CONFIG_SYSTEM= \
                    "$git_who_bin" table 2>&1
            )"
            if printf '%s\n' "$table_output" | grep -F "Test Author" >/dev/null; then
                PASS=$((PASS + 1))
                echo "  [ok] table output lists author 'Test Author'"
            else
                FAIL=$((FAIL + 1))
                echo "  [fail] table output missing author: $table_output"
            fi
        else
            FAIL=$((FAIL + 1))
            echo "  [fail] could not create initial commit in temp git repo"
        fi
        rm -rf "$repo_dir"
    else
        FAIL=$((FAIL + 1))
        echo "  [fail] could not create temp git repo"
    fi
else
    FAIL=$((FAIL + 1))
    echo "  [fail] git not found in PATH (git-who runtime dependency)"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <git-who-bin>\",\"discovered\":3,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
