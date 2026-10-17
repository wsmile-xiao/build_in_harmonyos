# hash-library

便携 C++ 哈希库，提供 CRC32、MD5、SHA1、SHA256、SHA3（224/256/384/512）、Keccak 和 HMAC（RFC 2104/2202/4231）。

## OHOS 适配

- 上游无构建系统（纯 .cpp/.h 源码），采用 Conan 手动编译
- 6 个算法实现编译为静态库 `libhash-library.a`（`-fPIC -O2 -std=c++17`）
- `digest` CLI 工具（计算文件摘要，支持 --crc/--md5/--sha1/--sha256/--keccak/--sha3）
- 无外部依赖，zlib License

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 8 | built | 上游 tag `hash_library_v8`（70cc9376） |

## 测试

- 上游测试 3/3 通过：`tests/tests.cpp`（100 组自动向量 + SHA/HMAC 系列）、`github-issue2.cpp`（重复 getHash 幂等）、`github-issue6.cpp`（SHA3-512 向量）
- test_package 消费者测试：SHA256/MD5/SHA1/CRC32/SHA3/Keccak/HMAC 已知向量断言 + 流式 API