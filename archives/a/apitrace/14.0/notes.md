# apitrace 14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: published

## Conan 适配

### 源码获取
- 主源码: GitHub archive tarball (https://github.com/apitrace/apitrace/archive/refs/tags/14.0.tar.gz)
- Git submodules: GitHub archive tarball 不包含 git submodules，需在 conanfile.py source() 中单独下载
  - thirdparty/brotli (google/brotli)
  - thirdparty/gtest (google/googletest)
  - thirdparty/libbacktrace (ianlancetaylor/libbacktrace)
  - thirdparty/libpng (apitrace/libpng fork)
  - thirdparty/snappy (google/snappy)
  - thirdparty/zlib (madler/zlib)
  - thirdparty/zstd (facebook/zstd)
  - thirdparty/directxmath (microsoft/DirectXMath)
  - frametrim/tests (apitrace/gltrim-tests)

### CMake 配置
- CMAKE_SYSTEM_NAME=Linux (OHOS 不被 CMake 识别，使用 Linux 兼容)
- ENABLE_GUI=OFF (无 Qt 依赖)
- ENABLE_X11=OFF (无 X11 依赖)
- ENABLE_EGL=OFF (无 EGL 依赖)
- BUILD_TESTING=OFF (跳过单元测试)
- ENABLE_CLI=ON (启用命令行工具)

### 构建产物
- bin/apitrace (主命令行工具)
- bin/gltrim (帧裁剪工具)
- lib/apitrace/scripts/ (Python 辅助脚本)

## 编译步骤

1. 从 GitHub 下载 apitrace 14.0 源码
2. 下载所有 git submodules 到 thirdparty/ 目录
3. 使用 CMake 构建：
   ```bash
   cmake -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_SYSTEM_NAME=Linux \
         -DENABLE_GUI=OFF \
         -DENABLE_X11=OFF \
         -DENABLE_EGL=OFF \
         -DBUILD_TESTING=OFF
   make -j2
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive tarball 缺少 submodules | git archive 不递归 submodule | conandata.yml 中列出所有 submodule URL+sha256，source() 中逐个下载 |
| 2 | CMake 不识别 OHOS 平台 | CMake 无 OHOS platform module | 设置 CMAKE_SYSTEM_NAME=Linux |
| 3 | test_package CMakeToolchain 重复 | generators 属性和 generate() 方法都创建了 CMakeToolchain | 从 generators 移除 CMakeToolchain，仅在 generate() 中创建 |

## 适配范围与限制 (R40)

apitrace 是图形 API 追踪工具，支持 OpenGL/Direct3D/Vulkan。在 OHOS 平台上的适配范围：
- CLI 工具 (apitrace, gltrim) 可用于处理和分析 trace 文件
- 图形 wrapper 库 (EGL/GL/X11) 在 OHOS 平台上不可用（已禁用）
- 实际的图形 API 追踪功能需要平台特定的 wrapper 实现，OHOS 上暂不支持
- 本次适配覆盖 CLI 工具链和 trace 文件处理功能

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + submodule 声明 |
| test_package/ | 测试包 |
| commands.json | 命令行工具声明 |
---

**编译结束**: 2026-08-27 15:11
**最终状态**: published
