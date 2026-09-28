#!/bin/sh
# test_kubo_migration.sh — 按上游 test-e2e/test.sh 语义真实执行 15→16 迁移测试，
# 并增加鸿蒙特有测试：用 OHOS 平台自带签名工具 binary-sign-tool 对安装产物做
# 真实签名校验（OHOS 的 AppSpawn 拒绝执行未签名 ELF，code signature 是鸿蒙
# 可运行的前提，这正是本配方 OHOS 适配的核心动作）。
#
# 上游 test.sh 用 `go run ..` 驱动，但在 OHOS 上 `go run` 生成的临时 ELF
# 未签名无法执行（权限被拒），故此处改用已构建+已签名（OHOS 时）的安装二进制，
# 测试逻辑与上游完全一致，另加鸿蒙签名验证：
#   1. OHOS code signature 校验（binary-sign-tool display-sign → self-sign）
#   2. -help 冒烟
#   3. 复制 repo-v15 → 正向迁移 → version=16 且 diff -r 与 repo-v16 一致
#   4. -revert 回退 → version=15 且 diff -r 与 repo-v15 一致
set -eu

BIN="$1"
FIXTURES="$2"
WORK="$3"

rm -rf "$WORK"
mkdir -p "$WORK"

echo "==> 1/4 OHOS signature check: $BIN"
# 鸿蒙特有：OHOS 的 AppSpawn 在 exec 时校验 ELF 的 code signature，未签名
# 产物无法运行。binary-sign-tool 是 OHOS 平台自带签名工具，此处直接对安装
# 产物执行 display-sign 做真实校验；输出 "code signature is not found" 即
# 未签名 → 测试失败（本配方 build() 中的 _sign_ohos_executable 会执行签名）。
SIGN_TOOL=""
for c in "${OHOS_BINARY_SIGN_TOOL:-}" "${BINARY_SIGN_TOOL:-}" /data/service/hnp/bin/binary-sign-tool; do
    if [ -n "$c" ] && [ -x "$c" ]; then
        SIGN_TOOL="$c"
        break
    fi
done
[ -z "$SIGN_TOOL" ] && SIGN_TOOL=$(command -v binary-sign-tool 2>/dev/null || true)
[ -z "$SIGN_TOOL" ] && {
    echo "FAIL: binary-sign-tool not found; cannot verify OHOS code signature"
    exit 1
}
"$SIGN_TOOL" display-sign -inFile "$BIN" > "$WORK/sign.out" 2>&1 || {
    echo "FAIL: binary-sign-tool display-sign failed"
    exit 1
}
grep -q "code signature is self-sign" "$WORK/sign.out" || {
    echo "FAIL: binary is NOT signed for OHOS (code signature is not found)"
    cat "$WORK/sign.out"
    exit 1
}
echo "    OK: OHOS-signed executable (self-sign verified)"

echo "==> 2/4 smoke: $BIN -help"
"$BIN" -help > "$WORK/help.out" 2>&1 || {
    echo "FAIL: -help returned non-zero"
    exit 1
}
grep -q "Usage of" "$WORK/help.out" || {
    echo "FAIL: -help output missing usage"
    exit 1
}

echo "==> 3/4 forward migration 15 -> 16"
cp -r "$FIXTURES/repo-v15" "$WORK/repo-test"
"$BIN" -verbose -path="$WORK/repo-test"
[ "$(cat "$WORK/repo-test/version")" = "16" ] || {
    echo "FAIL: version file not upgraded to 16"
    exit 1
}
# 迁移会生成 config.15-to-16.bak 备份文件；JC1 门禁禁止 .bak 入 git，
# 故 fixture 不含该文件。在副本上删除备份后与 repo-v16 fixture 对比，
# 原 repo-test 保留 .bak（第 3/3 步回退依赖 os.Rename(.bak -> config) 恢复）。
cp -r "$WORK/repo-test" "$WORK/repo-test-verify"
rm -f "$WORK/repo-test-verify/config.15-to-16.bak"
diff -r "$FIXTURES/repo-v16" "$WORK/repo-test-verify" || {
    echo "FAIL: migrated repo does not match repo-v16 fixture"
    exit 1
}
rm -rf "$WORK/repo-test-verify"

echo "==> 4/4 revert 16 -> 15"
"$BIN" -verbose -revert -path="$WORK/repo-test"
[ "$(cat "$WORK/repo-test/version")" = "15" ] || {
    echo "FAIL: version file not reverted to 15"
    exit 1
}
diff -r "$FIXTURES/repo-v15" "$WORK/repo-test" || {
    echo "FAIL: reverted repo does not match repo-v15 fixture"
    exit 1
}

rm -rf "$WORK"
echo "ALL TESTS PASSED (OHOS signature + help smoke + forward 15->16 diff + revert 16->15 diff)"
