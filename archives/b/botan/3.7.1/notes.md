# Botan 3.7.1 — Adaptation Notes (HarmonyOS PC aarch64)

## 软件概述

Botan 是现代化的 C++ 加密库，提供 AES/ChaCha20、RSA/ECC/EdDSA、SHA-2/SHA-3/BLAKE2、
HMAC/CMAC、TLS 1.2/1.3、随机数生成等广泛算法。3.7.1 相对 main 上已有的 3.6.1 是
版本升级件（依赖项 #14963）。

## 上游信息

- **上游版本**: 3.7.1（tag=3.7.1，无 v 前缀，git ls-remote 已验证）
- **上游源码**: https://botan.randombit.net/releases/Botan-3.7.1.tar.xz（官方主分发渠道；
  GitHub release 页 3.7.1 无二进制资产，`releases/download/3.7.1/*` 实测 404）
- **sha256**: fc0620463461caaea8e60f06711d7e437a3ad1eebd6de4ac29c14bbd901ccd1b（本地下载实测）
- **许可证**: BSD-2-Clause
- **构建系统**: 自研 Python configure.py + make（非 cmake/meson）

## 构建配置（3.6.1 → 3.7.1 增量差异）

```bash
python3 ./configure.py \
    --prefix=<package_folder> \
    --build-tool=make \
    --os=linux \
    --cc=clang \
    --cpu=arm64 \
    --build-targets=static,tests \
    --without-os-features=explicit_bzero \
    --without-documentation \
    --disable-modules=kyber,kyber_90s,kyber_common,kyber_round3,\
dilithium,dilithium_aes,dilithium_common,dilithium_round3,dilithium_shake,\
ml_kem,ml_dsa,slh_dsa_sha2,slh_dsa_shake,pqcrystals,tls13_pqc
```

与 3.6.1 的差异：
1. **新增 `--cpu=arm64`**：显式指定目标架构，启用 ARMv8 crypto SIMD 模块
   （aes_armv8 / sha2_*_armv8 / ghash_cpu 等，本机 aarch64 原生编译）。
2. **explicit_bzero 处理升级**：3.6.1 需要 configure 后 sed 改 build.h 注释掉
   `BOTAN_TARGET_OS_HAS_EXPLICIT_BZERO`；3.7.1 原生支持
   `--without-os-features=explicit_bzero` 干净参数（已实测 OHOS 头文件无此声明，
   Botan 内部回退到 volatile memset 清零）。
3. **PQC 禁用列表扩充**：3.7.x 新增 ml_kem / ml_dsa / slh_dsa_sha2 / slh_dsa_shake /
   pqcrystals / tls13_pqc 模块名（3.6.1 只有 kyber*/dilithium*）。这些模块的库代码
   依赖 OHOS clang-15 libc++ 未提供的 C++20 ranges 特性，编译失败，整族禁用。
4. **新增 `tests` 构建目标**：3.6.1 因 C++20 ranges 编不过测试而禁用测试；本次通过
   0001 号补丁修复 6 处 ranges 用法后，上游测试套件首次在 OHOS 上完整构建并运行。

## 补丁清单

| 补丁 | 文件 | 类型 | 说明 |
|------|------|------|------|
| 0001 | src/tests/test_utils_bitvector.cpp, src/tests/unit_x509.cpp | portability | `std::ranges::equal/find` → 经典迭代器对（2 文件 6 处，仅测试代码，库零改动） |
| 0002 | src/tests/tests.cpp | portability | `Test::temp_file_name` 硬编码 `/tmp` → 尊重 TMPDIR 环境变量（HarmonyOS PC /tmp 只读 EROFS；ivar 1.4.4 同型先例） |

## 上游测试（本地实测，2026-10-08）

- **测试形态**: 单体 runner `./botan-test`（configure.py --build-targets=tests 生成，
  src/tests/ 下 125 个测试源文件 + 4 个 runner 文件；BOTAN_REGISTER_TEST 注册宏
  实测 353 处；数据文件 54 个，全离线）
- **全量结果**: `Tests complete ran 3055115 tests in 43.39 sec all tests ok`
  （3055115 个测试断言，0 失败，100% 通过；TMPDIR 指向可写目录后）
- **运行环境**: 本机 HarmonyOS PC aarch64，LD_LIBRARY_PATH 指向 OHOS SDK
  libc++_shared.so
- 修复前唯一失败项：DataSinkFlush — "Failed to create temporary file"（/tmp 只读），
  0002 补丁修复后全绿

## 质量门禁结果

- G0 (编译成功): ✅ libbotan-3.a 25.3 MB（静态库）
- G1 (产物完整): ✅ 静态库 + 头文件（make install 完整）
- G2 (测试可运行): ✅ botan-test 在 OHOS aarch64 真实运行
- G3 (测试通过): ✅ 3,055,115 / 3,055,115（100%）
- G4 (文档): ⏭️ 跳过（--without-documentation）

## 已知限制

1. **共享库不构建**：3.6.1 发现的动态库运行时符号重定位问题在 3.7.1 依然存在
   （OHOS 加载器 vs SONAME 版本方案），维持 static-only 策略。
2. **PQC 模块族禁用**：kyber/dilithium/ml_kem/ml_dsa/slh_dsa/pqcrystals/tls13_pqc
   ——OHOS clang-15 libc++ 的 C++20 ranges 不完整，等工具链升级后可恢复。
3. explicit_bzero 以 `--without-os-features` 干净禁用，Botan 回退 volatile memset。

## 使用建议

1. 静态链接 `libbotan-3.a`，头文件在 `include/botan-3/`。
2. 需要后量子算法（ML-KEM/ML-DSA）的应用暂不可用本包。
