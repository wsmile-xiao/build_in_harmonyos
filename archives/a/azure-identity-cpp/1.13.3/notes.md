# azure-identity-cpp 1.13.3 Build Notes

## Source
- Official: https://github.com/Azure/azure-sdk-for-cpp (tag: azure-identity_1.13.3)
- tarball: https://codeload.github.com/Azure/azure-sdk-for-cpp/tar.gz/refs/tags/azure-identity_1.13.3
- SHA-256: 4e83559e53b475e25f6a142604a477609b271111982bd2c88c8a4fe371338fcc
- License: MIT

## 适配背景
- R16（r01/r02 审计对象）提交的是**未完成的 Autotools 模板配方**：构建系统与
  azure-sdk-for-cpp 实际 CMake 不符、`requirements()` 为空、无构建产物，
  G0-G4/finish=0 声称无效（r02 审计确认）。
- r03 确认正确分支 `feat/azure-identity-1.13.3` 与专用 worktree 不存在。
- r04 新建专用 worktree（pc1-19-azure-identity-1.13.3）并从真实 CMake 项目重新适配。

## Dependencies
- azure-core-cpp >= 1.16.4（required，token credential 基础设施）
- OpenSSL >= 3.5.6（required，非 Windows 平台用于签名/加密）

## OHOS Build Configuration
- Compiler: clang-15 (OHOS NDK, /data/service/hnp/bin/clang++)
- libc++: yes
- C++ standard: 17（CMakeToolchain 设置；上游默认 14 被 toolchain 覆盖为 17）
- Architecture: armv8
- Build type: Release
- Shared library: no（静态库，fPIC=ON）

## CMake Options
- BUILD_TESTING=OFF（上游 gtest 套件依赖网络/Azure 端点，test_package 消费者验证替代）
- AZ_ALL_LIBRARIES=OFF（只构建 azure-identity 子项目）
- WARNINGS_AS_ERRORS=OFF
- 构建入口: sdk/identity/azure-identity（cmake.configure build_script_folder）

## Patches（2 个，均基于 tag 源码逐字 diff 生成，不凭空改上游断言）
1. `patches/0001-cmake-modules-AzureTransportAdapters.cmake.patch`
   AzureTransportAdapters.cmake: `elseif (UNIX)` → `elseif (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`，
   使 HarmonyOS 被识别为 POSIX-like 平台（libcurl 传输默认选项）。
2. `patches/0002-sdk-identity-azure-identity-CMakeLists.txt.patch`
   sdk/identity/azure-identity/CMakeLists.txt: CMakeDeps 包名匹配 —
   `find_package(azure-core-cpp ...)` → `find_package(azure-core ...)`（azure-core-cpp 配方
   cmake_file_name=azure-core）；`find_package(OpenSSL)/OpenSSL::Crypto` →
   `find_package(openssl CONFIG)/openssl::openssl`（openssl 配方 CMakeDeps 目标名）。

## 历史坑（R16 模板违背的 SKILL 铁律）
- R26/R33: 系统同名库与构建环境：CMakeToolchain 生成编译器/标志，不裸用 `${CC}`。
- R34: test_package 必须实质调用被测 API：test.cpp 构造 ClientSecretCredential /
  EnvironmentCredential / ChainedTokenCredential / DefaultAzureCredential 并断言（5 断言，
  无网络调用，token 获取需真实租户故仅构造验证）。
- R39: 源码 URL 为官方 codeload.github.com 标签源。

## 验证记录（r04 本地，无远端授权）
- `conan create`（OHOS armv8 profile）: PASS（exit 0），test_package 4 个 credential 构造通过
- `conan-verify` G0-G4: PASS（G1 配方完整性 / G2 conan create / G3 系统同名库隔离 / G4 产物完整性）
- finish W3 本地 CI 模拟: JC 门禁报 3 个 junk 文件，全部位于**其他库** main 基线
  （isa-l_crypto/2.26/conandata.yml.orig、middleclass/4.1.1/conandata.yml.ghfast-bak、
  swift-corelibs-blocksruntime/6.3.3/.staging-verified），与本库无关（外部首错，r04 报告注明）。
- 本库配方文件经 JC 规则模式逐一核对：无 junk 命中。
---

**编译结束**: 2026-08-25 11:54
**最终状态**: built
