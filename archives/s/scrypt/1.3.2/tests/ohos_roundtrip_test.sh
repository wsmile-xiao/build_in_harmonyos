#!/bin/sh
# HarmonyOS 专项测试：scrypt 1.3.2 文件加解密往返验证
# 在 OHOS (aarch64-unknown-linux-ohos, clang 15) 平台上实际运行：
#   1. scrypt --version 输出 1.3.2
#   2. 用已知口令加密明文文件 -> 密文可解密且内容与原文一致
#   3. 错误口令解密必须失败（scrypt 完整性校验 HMAC 生效）
# 与上游 01-09 场景脚本不同，本测试是本轮新增的独立验证入口。
set -u

SCRYPT_BIN="${1:-./scrypt}"
WORKDIR="${2:-$(mktemp -d "${TMPDIR:-/tmp}/scrypt-ohos-test.XXXXXX")}"

echo "==> scrypt bin: ${SCRYPT_BIN}"
echo "==> workdir: ${WORKDIR}"

fail() {
    echo "FAIL: $1"
    exit 1
}

# 1) 版本核验
VER="$("${SCRYPT_BIN}" --version 2>&1)"
echo "==> version: ${VER}"
[ "${VER}" = "scrypt 1.3.2" ] || fail "version mismatch: ${VER}"

# 2) 加解密往返
PLAINTEXT="${WORKDIR}/plain.txt"
ENCRYPTED="${WORKDIR}/plain.enc"
DECRYPTED="${WORKDIR}/decrypted.txt"
printf 'HarmonyOS scrypt roundtrip test payload 0123456789\n' > "${PLAINTEXT}"
PASSPHRASE="ohos-test-passphrase"

# 使用 --passphrase env:VAR 避免交互输入
PASSPHRASE="${PASSPHRASE}" "${SCRYPT_BIN}" enc --passphrase env:PASSPHRASE \
    "${PLAINTEXT}" "${ENCRYPTED}"
[ $? -eq 0 ] || fail "scrypt enc failed"

PASSPHRASE="${PASSPHRASE}" "${SCRYPT_BIN}" dec --passphrase env:PASSPHRASE \
    "${ENCRYPTED}" "${DECRYPTED}"
[ $? -eq 0 ] || fail "scrypt dec failed"

cmp -s "${PLAINTEXT}" "${DECRYPTED}" || fail "decrypted content mismatch"
echo "==> roundtrip OK (encrypt -> decrypt -> content identical)"

# 3) 错误口令必须失败（scrypt 格式带 HMAC 完整性校验）
WRONG_OUT="${WORKDIR}/wrong.txt"
PASSPHRASE="wrong-passphrase" "${SCRYPT_BIN}" dec --passphrase env:PASSPHRASE \
    "${ENCRYPTED}" "${WRONG_OUT}" 2>/dev/null
RC=$?
echo "==> wrong-passphrase decrypt exit code: ${RC}"
[ "${RC}" -ne 0 ] || fail "wrong passphrase decrypt should fail"

echo "==> ALL OHOS TESTS PASSED"
rm -rf "${WORKDIR}"
exit 0
