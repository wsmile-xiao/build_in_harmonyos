# vulkan-utility-libraries vulkan-sdk-1.4.350.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 配置（Release模式）
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=OFF \
    -DVUL_ENABLE_INSTALL=ON \
    ..

# 编译
make -j2

# DESTDIR 模式安装
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-vulkan-utility-libraries-vulkan-sdk-1.4.350.0

# Debug 模式构建（用于 debug 包）
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
    -DCMAKE_BUILD_TYPE=Debug \
    -DBUILD_TESTS=OFF \
    -DVUL_ENABLE_INSTALL=ON \
    ..
make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-vulkan-utility-libraries-vulkan-sdk-1.4.350.0-debug

# 无 DESTDIR 安装到 DEFAULT_PREFIX
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS 平台 | CMake 未内置 HarmonyOS 平台定义 | 非阻塞警告，编译正常完成 |
| 2 | 测试套件依赖 GTest 和 magic_enum | tests/CMakeLists.txt 需要 find_package(GTest REQUIRED CONFIG) 和 find_package(magic_enum REQUIRED CONFIG) | BUILD_TESTS=OFF，cmd-pkgs 无预编译包，记录跳过原因 |

## 源码修改

无源码修改，无补丁文件。

## 依赖版本

- VulkanHeaders: vulkan-sdk-1.4.350.0 (已预编译安装)
- clang: 15.0.4

## 验证结果

```bash
# CMake find_package 验证
cmake --find-package -DNAME=VulkanUtilityLibraries -DCOMPILER_ID=Clang -DLANGUAGE=CXX -DMODE=EXIST
# → VulkanUtilityLibraries found.

# 安装产物
ls /storage/Users/currentUser/usr/local/lib/libVulkan*.a
# → libVulkanLayerSettings.a, libVulkanSafeStruct.a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vulkan-utility-libraries-vulkan-sdk-1.4.350.0-ohos-aarch64.tar.gz | 7.7MB | Release 预编译包 |
| vulkan-utility-libraries-vulkan-sdk-1.4.350.0-ohos-aarch64-debug.tar.gz | 16.5MB | Debug 预编译包 |

## 注意事项

- vulkan-utility-libraries 是纯 header+static library 项目，无可执行文件
- 测试套因缺少 GTest/magic_enum 而跳过，不阻塞发布
- CMake 的 "System is unknown" 警告不影响编译结果
---

**编译结束**: 2026-05-28 11:15
**最终状态**: built
