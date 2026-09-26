# Test Report — hash-library 8

**Date**: 2026-09-22
**Build System**: custom（上游无构建系统，纯 .cpp/.h 源码库；Conan recipe 手动逐 TU 编译）
**Platform**: HarmonyOS PC (aarch64, clang-15, libc++, conan ohos-aarch64 profile, shared=False)
**上游 tag**: hash_library_v8 = 70cc93763d49a24c4536c7f0a23248f9b40e30f5

## Test Results（双口径台账，详见 reports/upstream-test-ledger.md）

**上游源码声明独立用例数 (source_declared_total)**: 3
（tests/tests.cpp 主套件 + tests/github-issue2.cpp + tests/github-issue6.cpp，
见 upstream-test-ledger.md 逐项清单；digest.cpp 为 CLI 示例非测试）
**当前配置可执行用例数 (configured_executable_total)**: 3（无互斥编译分支，全实例化）
**实际执行并通过 (executed_passed_total)**: 3/3
**未运行/未实例化**: 0
**全量通过率**: 3/3 = 100%（`executed_passed_total/source_declared_total`；
当前配置可执行集合通过率 3/3 = 100%）

| 入口 | 源码声明 | 构建条件 | 构建目标 | 执行结果 |
|------|---------|---------|---------|---------|
| 1 tests/tests.cpp 主套件 | tests.cpp `int main`（100 组 TestSet 向量 + SHA1/SHA2-256/SHA3-256/512/224/Keccak-224 + HMAC(MD5/SHA1/SHA256) RFC2202/4231 + 1MB 向量） | 无宏门控，直编 | tests-run | 通过（`all tests ok`，rc=0） |
| 2 tests/github-issue2.cpp | issue#2 回归：5 算法重复 getHash() 幂等 | 无宏门控，直编 | issue2 | 通过（rc=0） |
| 3 tests/github-issue6.cpp | issue#6 回归：SHA3-512 已知向量(72a5f501151ca974002f34) | 无宏门控，直编 | issue6 | 通过（rc=0） |

- 实际执行命令与日志：见 ~/.oh-runner/logs/hash-library-8/ 与
  reports/upstream-test-ledger.md（SHA-256 见 W3 日志与 .ci-result.json）
- 样例/基准/框架排除：digest.cpp 为 CLI 示例工具（非测试），不计入独立用例。

## 本地真实验证（全部通过）

1. **静态库编译** (rc=0): `clang++ -fPIC -O2 -std=c++17 -c {crc32,md5,sha1,sha256,sha3,keccak}.cpp`
   → `llvm-ar rcs libhash-library.a` + `llvm-ranlib`，共 6 TU 全编译成功
2. **digest CLI** (rc=0): `./digest readme.md --sha256` →
   `4c84a5d0d1e44bc44bc4dcb2949250083c8d887e7e9d68b18a2fe93d1aa4e58f`（与 sha256sum 一致）
3. **上游测试** (rc=0): tests-run / issue2 / issue6 全通过（见上表）
4. **Conan 配方门禁** (conan-verify G0-G4+L2/L4/L5 全 PASS): conan create 干净构建通过，
   test_package 消费者测试 1/1 Passed（ctest `100% tests passed`）
5. **消费者用例** (test_package/test_consumer.cpp, rc=0): 仅通过已安装公开头
   （<crc32.h>/<md5.h>/<sha1.h>/<sha256.h>/<sha3.h>/<keccak.h>/<hmac.h>）+ 公开 API
   （SHA256()/MD5()/SHA1()/CRC32()/SHA3()/Keccak()/hmac<T>()/add()/getHash()）
   编译链接运行，输出 `test_hash-library: all consumers assertions passed`
6. **HarmonyOS 专项测试** (tests-ohos/ohos_test.cpp, rc=0): 14 项断言全 PASS
   （NIST 已知向量、HMAC RFC2202/4231、流式分块 API、1MB 'a' 向量、getHash 幂等），
   输出 `OHOS test: all checks passed`

## 质量备注

- upgrade 版本号 "8" 为单字符（上游 tag hash_library_v8），Conan 制品版本经
  set_version() 归一化为 "v8"（复用 DRAFT-strong_type-9 知识，见 knowledge-candidate-ledger.md）
- 无外部依赖（纯 C++17，zlib License）