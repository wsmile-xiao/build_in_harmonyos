# CastXML 0.7.0 适配笔记

## 适配状态: built (等待 PR CI/人工审核)

## 问题描述
CastXML 编译成功，但二进制因 LLVM 共享库 CommandLine 选项重复注册问题无法运行。
已通过 patches/0007 和 0008 修复。

## 详细分析
### 历史基线问题
- OHOS SDK 的 LLVM 位于 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm`
- 原 baseline 同时 NEested libLLVM-15.so 和 libclang-cpp.so，两库各自注册 CommandLine options
- 导致 `LLVM ERROR: inconsistency in registered CommandLine options`，所有 3919 个 CTest 失败

### 修复方案
1. **patch 0007**: 移除 src/CMakeLists.txt 中的 `llvm_config()` 调用，避免链接 libLLVM-15.so
2. **patch 0008**: 移除 castxml.cxx 中的 `llvm::InitLLVM` 依赖，改用直接 argv 初始化
3. 仅保留 libclang-cpp.so 作为唯一 LLVM/Clang 共享库依赖

### 验证结果
- readelf -d: 仅 NEED libclang-cpp.so, libc++_shared.so, libc.so（无 libLLVM-15.so）
- castxml --version: exit 0
- ctest -j4: 3919/3919 PASSED (132.78s)

## 上游测试情况
- BUILD_TESTING=ON 已启用，ctest 已执行
- 上游 3919 个测试全部通过
- test_package 通过 CMake ctest 验证 castxml --version 可调用

## 生成的 Conan 配方
- conanfile.py: CMake 构建系统，已配置 LLVM_DIR/Clang_DIR，LLVM 路径通过 OHOS_SDK_LLVM_ROOT 环境变量获取
- conandata.yml: 8 个补丁（0001-0008），源码 URL 和 SHA256 已验证
- test_package/: 基本测试框架已生成，验证 castxml 二进制可安装可调用

## 下一步
1. 等待 PR CI 通过
2. 等待 AI Review
3. 所有问题闭环后等待人工审核
---

**编译结束**: 2026-07-24
**最终状态**: published
