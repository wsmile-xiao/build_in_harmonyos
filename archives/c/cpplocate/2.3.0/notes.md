# cpplocate 2.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 官方源码: https://github.com/cginternals/cpplocate (v2.3.0 tarball, sha256 07c9ccaa…cbb6)
2. 原生探索构建（SYSTEM_LINUX 定义注入，验证构建入口与上游测试）:
   ```bash
   cmake .. -DBUILD_SHARED_LIBS=ON -DOPTION_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_C_FLAGS=-DSYSTEM_LINUX -DCMAKE_CXX_FLAGS=-DSYSTEM_LINUX
   make -j4
   ```
3. 上游测试（googletest/gmock 1.17.0，pkg-config 注入）：liblocate-test 41/41、cpplocate-test 10/10 通过。
4. Conan 配方验证：`ohc-run.py conan-verify cpplocate 2.3.0 --profile ohos-aarch64` → G0-G4 全通过。
5. finish W3 本地 CI 模拟通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | liblocate.c 报 `Dl_info`/`getpwuid`/`struct passwd` 未声明 | OHOS CMAKE_SYSTEM_NAME=HarmonyOS 生成 `SYSTEM_HARMONYOS` 宏，上游无该分支，平台头未包含 | 补丁 0001: CompileOptions.cmake 将 OHOS/HarmonyOS 映射为 SYSTEM_LINUX（Linux-userland 兼容） |
| 2 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed" | 上游 `cmake_minimum_required(3.0)` 被 CMake 4.x 拒绝 | conanfile generate() 设置 cache_variables `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | conan create 阶段 CMakeDeps 报 `Library 'liblocate' not found` | 上游 liblocate 安装产物为 `liblocate.so`（空文件前缀），conan 按默认 lib 前缀找不到 | 只暴露 `cpp_info.libs=["cpplocate"]`（liblocate 源码已内嵌进 libcpplocate） |
| 4 | gtest 1.17.0 要求 C++17，上游测试目标锁 C++11 | gtest 版本要求 | 探索构建测试验证用 C++17；配方构建不开上游测试（OPTION_BUILD_TESTS=OFF） |
| 5 | W3 junk_check 拦到其他库 HEAD 基线文件（embree/.submit-state.json 等 3 个） | full 模式扫描整仓 | 已本地提交 cpplocate 变更后 W3 走 incremental 模式只检查本 PR 文件；基线噪声哈希记录、原样未动 |

## 源码修改

- `patches/0001-cmake-CompileOptions.cmake.patch`：CompileOptions.cmake 增加 OHOS/HarmonyOS → SYSTEM_LINUX 映射（+6/-1）。

## 依赖版本

- 构建期：无第三方依赖（库本体自包含 liblocate）。
- 测试期：googletest/gmock 1.17.0（仅本地验证上游测试用，配方 OPTION_BUILD_TESTS=OFF）。

## 验证结果

```bash
# 上游测试（51 个独立 TEST 用例，全通过）
liblocate-test  → [ PASSED ] 41 tests
cpplocate-test  → [ PASSED ] 10 tests
# HarmonyOS 专项测试
test_cpplocate_hmos → ALL_CPPLOCATE_HMOS_ASSERTIONS_PASSED (exit 0)
# 消费者验证
test_cpplocate → test_cpplocate: OK (exit 0)
# 配方验证
ohc-run.py conan-verify cpplocate 2.3.0 --profile ohos-aarch64 → 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan CMake 配方（shared 开关、CMP 兼容、禁上游测试） |
| conandata.yml | 官方 tarball + sha256 + 补丁注册 |
| patches/0001-*.patch | OHOS→SYSTEM_LINUX 平台宏映射 |
| test_package/ | 消费者测试 + HarmonyOS 专项测试 + MANIFEST.yml |

## 注意事项

- 上游 liblocate 库安装产物无 lib 前缀（`liblocate.so`），conan 只导出 cpplocate 目标；
  直接消费 C API 的用户需手动链接安装目录中的 liblocate.so。
- 平台宏映射通过 cmake 层完成（CompileOptions.cmake），未改动 liblocate.c 源码本身。
---

**编译结束**: 2026-09-02 14:12
**最终状态**: built
