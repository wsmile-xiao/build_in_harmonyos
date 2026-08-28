# aws-lc-tools

## 简介
aws-lc-tools 是 [aws/aws-lc](https://github.com/aws/aws-lc) 项目的命令行工具子包，
提供 BoringSSL 风格的 `bssl` 多功能工具，以及 OpenSSL 兼容的 `openssl` 命令与
`c_rehash` 脚本。aws-lc 是 AWS 密码团队维护的通用密码库（BoringSSL 分支）。

## 包含的工具
- `bssl` — 多功能命令行工具：`version`、`sha256sum/md5sum/sha*sum`、`rand`、
  `genrsa`、`generate-ed25519`、`sign`、`ciphers`、`client/server (s_client/s_server)`、
  `pkcs12`、`speed` 等
- `openssl` — OpenSSL 兼容命令行：`version`、`dgst`、`sha1`、`md5`、`rand`(经 enc)、
  `genrsa`、`rsa`、`req`、`x509`、`verify`、`enc`、`pkey`/`pkeyutl` 等
- `c_rehash` — 证书目录哈希重建脚本（perl）

## OHOS 适配
- **构建系统**: CMake；`-DBUILD_TOOL=ON` 构建工具目标
- **Go 依赖**: 无 Go 工具链时必须 `-DDISABLE_GO=ON`，使用上游 generated-src/ 预生成代码
- **汇编优化**: OHOS 上 `CMAKE_SYSTEM_PROCESSOR=unknown`，需 `-DOPENSSL_NO_ASM=ON`
  启用纯 C 回退实现（否则汇编符号链接失败）
- **单核构建预算**: hmbs 真机预检为单任务编译且有硬性墙钟预算，整树按
  `-O1 -DNDEBUG`（替换 Release 默认 `-O3`）编译，为链接、签名与全量上游测试
  预留预算；上游支持可变优化级别（memcmp_invalid_stripped_check 按实际
  Release flags 运行期探测）
- **源码下载**: 145MB 归档直连 GitHub 过慢，conandata.yml 按序回退
  gh-proxy.com / mirror.ghproxy.com 镜像（仓库 CI 维护的映射），sha256 校验不变
- **静态链接 (R26)**: libcrypto/libssl 为系统同名库，必须以静态库形式链接进工具，
  本包不安装任何 `.so`/`.a`（库需求请使用 `aws-lc` 库包）
- **签名要求**: 鸿蒙内核拒绝执行未签名 ELF，工具需 `binary-sign-tool -selfSign` 自签名

## 测试
上游测试运行器为 Go 程序（util/all_tests.go + util/all_tests.json 清单）。本配方在
BUILD_TESTING=ON 下编译 gtest 测试套件，并按 all_tests.json 的 aarch64 适用条目直接
执行各测试二进制（crypto_test、ssl_test、mem_test/mem_set_test、
rand_isolated/tree_drbg_jitter_entropy_isolated、tool_openssl_test 等），
聚合结果输出 HMBS_UPSTREAM_TEST_RESULT。test_package 另对安装后的 bssl/openssl
二进制做真实功能冒烟验证（摘要已知值校验、随机数长度、RSA 密钥生成与检查等）。
例外：`crypto/dynamic_loading_test` 在静态构建下是空转 PASS 桩（需要共享库 libcrypto.so），
不纳入执行集。

## 依赖
无外部 Conan 依赖（自包含构建）。构建期工具链为 cmake + clang；`DISABLE_GO=ON` 后使用
上游 generated-src/ 预生成代码，无需 Go 工具链，perl 缺失时上游同样回退预生成代码。

## 参考
- 官方源码: https://github.com/aws/aws-lc
- 库包适配: archives/a/aws-lc/
