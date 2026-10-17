#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for tboot 1.10.5 (aarch64 OHOS)
#
# Every shipped tool is exercised with real inputs, not just --help:
#
#   * tb_polgen builds a measured-launch policy, which makes it hash a command
#     line and an image file with OpenSSL (EVP_sha256) and fold both digests
#     together.  B4 pins the resulting value to the upstream algorithm
#     SHA256(SHA256(cmdline) || SHA256(image)), so a broken libcrypto cannot
#     pass this test.
#   * lcptools-v2 builds a policy element, a policy list (self-verified against
#     the TPM2.0 structures) and a policy + policy data pair.
#   * the OH-* assertions cover the HarmonyOS specifics of this port: the
#     decompression scratch file must follow $TMPDIR (/tmp is a read-only mount
#     on OHOS — E002), and the executables must be pure aarch64 OHOS binaries
#     with no dependency beyond libc.
#
# Assertion count: 22 (see test_package/MANIFEST.yml).
set -u

# 测试工作目录：优先可写的 $TMPDIR（OHOS 的 /tmp 是只读挂载，E002），
# 退出时删除，绝不把中间产物留在 recipe 目录里。
BASE="${1:-${TMPDIR:-}}"
if [ -z "$BASE" ] || [ ! -d "$BASE" ] || [ ! -w "$BASE" ]; then
    BASE="$(pwd)"
fi
WORK="$(mktemp -d "$BASE/tboot-test-XXXXXX")" || { echo "[FAIL] 无法创建测试工作目录"; exit 1; }
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1

pass=0
fail=0

ok()  { printf '  [PASS] %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  [FAIL] %s\n' "$1"; fail=$((fail + 1)); }
check() { if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }

TOOLS="lcp2_mlehash lcp2_crtpol lcp2_crtpollist lcp2_crtpolelt tb_polgen txt-stat txt-parse_err"
GOLDEN_HASH="1d 76 7f d6 7e 62 21 01 4b bb 26 14 cd 53 1f f7 f9 84 fb 4a ac 5b f5 f7 35 e2 22 8b 50 0f 52 55"

echo "== A. 工具可用性 =="
for t in $TOOLS; do
    command -v "$t" > /dev/null 2>&1
    check $? "A: $t 已安装且在 PATH 中"
done

echo "== B. tb_polgen 端到端（策略创建 / 追加 / 校验 / 黄金哈希） =="
printf 'hello tboot image\n' > image.bin

tb_polgen --create --type nonfatal pol.bin > /dev/null 2>&1
check $? "B1: tb_polgen --create --type nonfatal 成功（策略文件已生成）"

tb_polgen --add --num 0 --pcr none --hash image \
          --cmdline "root=/dev/sda1" --image image.bin pol.bin > /dev/null 2>&1
check $? "B2: tb_polgen --add --hash image 成功（libcrypto EVP 摘要 + 策略写回）"

show_out="$(tb_polgen --show pol.bin 2>&1)"
printf '%s\n' "$show_out" | grep -q "num_entries: 1"
check $? "B3: --show 回读策略，num_entries = 1"

printf '%s\n' "$show_out" | grep -q "$GOLDEN_HASH"
check $? "B4: 黄金哈希匹配 SHA256(SHA256(cmdline)||SHA256(image))（libcrypto 真实生效）"

echo "== C. lcptools-v2 端到端 =="
lcp2_crtpolelt --create --type custom \
    --uuid "{0x00112233, 0x4455, 0x6677, 0x8899, {0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff}}" \
    --out elt.bin > /dev/null 2>&1
check $? "C1: lcp2_crtpolelt --create（custom 元素）成功"

elt_out="$(lcp2_crtpolelt --show elt.bin 2>&1)"
printf '%s\n' "$elt_out" | grep -q "0x00112233"
check $? "C2: lcp2_crtpolelt --show 回显 UUID"

lcp2_crtpollist --create --out list.bin --listver 0x300 elt.bin > /dev/null 2>&1
check $? "C3: lcp2_crtpollist --create（LCP_POLICY_LIST_2_1）成功"

list_out="$(lcp2_crtpollist --show list.bin 2>&1)"
printf '%s\n' "$list_out" | grep -q "Verify TPM2.0 Policy List 2.1 success"
check $? "C4: --show 回读策略列表并通过 TPM2.0 结构自校验"
printf '%s\n' "$list_out" | grep -q "Version: 0x300"
check $? "C5: 策略列表版本为 0x300（LCP_POLICY_LIST_2_1）"

lcp2_crtpol --create --alg sha256 --type list --sign ecdsa-p256 \
            --pol pol.out --data data.bin list.bin > /dev/null 2>&1
[ $? -eq 0 ] && [ -s pol.out ] && [ -s data.bin ]
check $? "C6: lcp2_crtpol --create 生成策略文件 + 策略数据文件"

err_out="$(txt-parse_err 0x00000005 2>&1)"
printf '%s\n' "$err_out" | grep -q "ERRORCODE: 0x00000005"
check $? "C7: txt-parse_err 解析 TXT.ERRORCODE（输出解码结果）"

echo "== D. 鸿蒙特有断言 =="
# OH-1/OH-2: the decompression scratch file of lcp2_mlehash must live in
# $TMPDIR (patch 0004).  Upstream used tmpfile(), which always creates it in
# /tmp — a read-only mount on OHOS, where the tool could not work at all.
TMPDIR="$WORK" lcp2_mlehash --create --alg sha256 --verbose image.bin > mle_ok.log 2>&1
grep -q "creating a temporary file to uncompress ... : succeeded" mle_ok.log
check $? "OH-1: TMPDIR 可写时 lcp2_mlehash 解压临时文件成功"

TMPDIR="$WORK/does-not-exist" lcp2_mlehash --create --alg sha256 --verbose image.bin > mle_bad.log 2>&1
grep -q "creating a temporary file to uncompress ... : failed" mle_bad.log
check $? "OH-2: TMPDIR 不可用时失败（证明临时文件确实建在 \$TMPDIR，而非固定 /tmp）"

if [ "$(TMPDIR=/tmp lcp2_mlehash --create --alg sha256 --verbose image.bin 2>&1 | grep -c 'temporary file to uncompress ... : failed')" != "0" ]; then
    echo "  [info] /tmp 在本平台为只读挂载（E002）：上游 tmpfile() 直接不可用"
fi

abi_bad=0
for t in $TOOLS; do
    bin="$(command -v "$t")"
    readelf -h "$bin" 2>/dev/null | grep -q "AArch64" || abi_bad=1
    [ "$(readelf -d "$bin" 2>/dev/null | grep -c '(NEEDED)')" = "1" ] || abi_bad=1
    readelf -d "$bin" 2>/dev/null | grep -q "libc.so" || abi_bad=1
done
check $abi_bad "OH-3: 7 个可执行文件均为 ELF64/AArch64，DT_NEEDED 仅 libc.so（openssl/zlib 静态链接）"

runpath_bad=0
for t in $TOOLS; do
    bin="$(command -v "$t")"
    if readelf -d "$bin" 2>/dev/null | grep -qE "RUNPATH|RPATH"; then runpath_bad=1; fi
done
check $runpath_bad "OH-4: 可执行文件不含 RUNPATH/RPATH（无构建机路径泄漏）"

echo "-------------------------------------------"
echo "tboot test_package: ${pass} passed, ${fail} failed (total $((pass + fail)))"
[ "$fail" -eq 0 ] || exit 1
