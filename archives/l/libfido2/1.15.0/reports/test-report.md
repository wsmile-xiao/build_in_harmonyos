# libfido2 1.15.0 Test Report

- Date: 2026-09-04
- Upstream source SHA-256: `abaab1318d21d262ece416fb8a7132fa9374bda89f6fa52b86a98a2f5712b61e`
- Profile: `ohos-aarch64`（os=OHOS arch=armv8 clang 15, aarch64-linux-ohos）
- Conan package ID: `6acfa1f550b2f3f22b23ce0ab84de7cac1ac93fb`（shared=True build_tools=True）

## Upstream Tests

上游 libfido2 自带 regress 测试套件（regress/，无硬件依赖的纯逻辑用例），
BUILD_TESTS=ON 时构建 7 个测试可执行文件（regress_compress 仅在
BUILD_STATIC_LIBS 时编入，本配方默认 shared 未构建）。

HarmonyOS PC W3 conan create（BUILD_TESTS=ON）构建产物实测：

| 测试 | 结果 |
|------|------|
| regress_assert | PASS |
| regress_cred | PASS |
| regress_dev | PASS |
| regress_eddsa | PASS |
| regress_es256 | PASS |
| regress_es384 | PASS |
| regress_rs256 | PASS |

- HarmonyOS PC W3 upstream regress: 7/7 passed
- 未运行的用例：regress_compress（BUILD_STATIC_LIBS-only，shared 配置不构建，
  属于上游构建矩阵差异而非平台豁免）

运行方式：本机即 OHOS aarch64 设备，`LD_LIBRARY_PATH=<pkg>/lib ./regress_*`
直接执行，7/7 退出码 0。

## Added Consumer Tests

Conan test_package 构建独立消费者可执行文件 test_libfido2，实质调用被测包
API：fido_init / fido_dev_new / fido_dev_free / es256_pk_new /
es256_pk_from_ptr（uncompressed 与 x||y 两种格式，公钥取上游
regress/es256.c 的 p256v1_raw 合法用例）/ es256_pk_free / rs256_pk_new /
rs256_pk_free / eddsa_pk_new / eddsa_pk_free / fido_strerr。

- HarmonyOS PC W3 consumer test_package: 1/1 passed
  （conan create 的 test() 阶段真实执行，输出
  "libfido2 test_package OK: ... all passed"）

## CLI Tools Verification（产物完整性）

安装包 bin/ 下 3 个命令行工具实测（LD_LIBRARY_PATH=<pkg>/lib）：

| 工具 | 验证 | 结果 |
|------|------|------|
| fido2-token -V | 版本输出 | `1.15.0` |
| fido2-token -L | 枚举设备（无设备时正常退出） | exit 0 |
| fido2-assert -V | usage 输出 | 正常 |
| fido2-cred -V | usage 输出 | 正常 |

## Test Data Summary

- 上游测试通过率：7/7（100%）
- 新增 test_package 通过率：1/1（100%）
- conan create 最终 exit code：0

## Evidence

- conan create 完整日志：`$HOME/tmp/fido-create-run9.log`（W3 本轮）
- SONAME/NEEDED 验证：`llvm-readelf -d` 输出见 notes.md「SONAME 问题的详细证据链」
- 依赖均来自制品仓 ohpcd（libcbor/0.10.2、openssl/3.5.6、zlib/1.3.1）
