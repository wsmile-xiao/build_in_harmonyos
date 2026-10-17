#!/data/service/hnp/bin/bash
# test_package/test.sh — git CLI smoke test (R34: 真实执行被测包二进制)
# GIT_BIN 由 test_package/conanfile.py 注入（被测包内 git 绝对路径），
# 包被移除时（CI 破坏性反向验证）此测试必须失败。
set -euo pipefail

: "${GIT_BIN:?GIT_BIN not set — test must fail without the package}"
test -x "$GIT_BIN" || { echo "❌ $GIT_BIN missing (package removed?)"; exit 1; }

echo "[test] $GIT_BIN --version"
V=$("$GIT_BIN" --version)
echo "[test] $V"
case "$V" in
  "git version 2.45.2") echo "✅ --version OK" ;;
  *) echo "❌ unexpected version: $V"; exit 1 ;;
esac

# E101/E2154: HMDFS UID 映射使仓库目录属主与运行身份错位，git 2.35+
# safe.directory 所有权检查拒绝仓库（E1 实证 rev-parse 报 dubious
# ownership → config 报 fatal: not in a git directory，CI #61158/#61292）。
# 包内 etc/gitconfig 的 [safe] directory=* 依赖 RUNTIME_PREFIX 解析系统
# 配置路径，CI 沙盒 /proc 受限时失效（//share 双斜杠警告即前缀为空）。
# 改用 GIT_CONFIG_GLOBAL/SYSTEM（git ≥2.32）显式注入，与目录位置无关。
export GIT_CONFIG_SYSTEM=/dev/null
GIT_TEST_GLOBAL="${TMPDIR:-/tmp}/gitcfg-$$"
printf '[safe]\n\tdirectory = *\n' > "$GIT_TEST_GLOBAL"
export GIT_CONFIG_GLOBAL="$GIT_TEST_GLOBAL"

TD="${TMPDIR:-$HOME/tmp}/git-test-$$"
mkdir -p "$TD"
trap 'rm -rf "$TD" "$GIT_TEST_GLOBAL"' EXIT

echo "[test] git init (share/git-core/templates 完整性)"
"$GIT_BIN" init "$TD/repo" > /dev/null
cd "$TD/repo"

echo "[test] git config + add + commit"
"$GIT_BIN" config user.name tester
"$GIT_BIN" config user.email tester@example.com
echo hello > f.txt
"$GIT_BIN" add f.txt
"$GIT_BIN" commit --no-gpg-sign -m initial > /dev/null

echo "[test] git cat-file（zlib 对象存储链路）"
"$GIT_BIN" cat-file -p 'HEAD^{tree}' | grep f.txt

echo "[test] git log"
"$GIT_BIN" log --oneline | grep -q initial

echo "✅ git CLI smoke test passed"
