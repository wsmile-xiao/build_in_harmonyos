# libtpms/0.10.2 测试报告

## 上游测试（make check）

| 测试 | 结果 |
|------|------|
| base64decode.sh | PASS |
| fuzz.sh | PASS |
| nvram_offsets | PASS |
| object_size | PASS |
| tpm2_createprimary.sh | PASS |
| tpm2_cve-2023-1017.sh | PASS |
| tpm2_cve-2023-1018.sh | PASS |
| tpm2_pcr_read.sh | PASS |
| tpm2_selftest.sh | PASS |
| tpm2_setprofile.sh | PASS |

汇总: `TOTAL: 10  PASS: 10  FAIL: 0  ERROR: 0`

## 消费者测试（test_package）

- 测试源: `test_package/test.c`
- 调用 API: `TPMLIB_GetVersion()`
- 结果: 返回非零版本号（`0x00001002`），通过

## 补丁

- `patches/0002-tests-support-harmonyos-stat.patch`（test）

## 平台

- 系统: HarmonyOS (aarch64, OHOS 6.0)
- 编译器: clang/clang++ 15.0.4
- 依赖: openssl/3.5.6
