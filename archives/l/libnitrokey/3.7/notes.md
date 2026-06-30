# libnitrokey 3.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: curl -L -k 从 GitHub 下载 v3.7 tarball
2. 解压源码: tar -xzf libnitrokey-3.7.tar.gz
3. 创建构建目录: mkdir build && cd build
4. 修改 CMakeLists.txt: cmake_minimum_required VERSION 3.1 -> 3.5（CMake 4.x 兼容性）
5. 运行 cmake 配置: cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
6. 编译: make -j2
7. Staging 安装: make install DESTDIR=/storage/Users/currentUser/test-install-libnitrokey-3.7

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败：cmake_minimum_required VERSION < 3.5 已被移除 | CMake 4.1.2 移除了对旧版本的兼容性支持 | 修改 CMakeLists.txt，将 VERSION 3.1 改为 3.5 |
| 2 | HMDFS 文件系统不支持硬链接（shutil.copytree os.link） | 鸿蒙平台 HMDFS 文件系统限制 | 手动使用 cp -r 复制源码目录 |

## 源码修改

- CMakeLists.txt: 第 6 行，cmake_minimum_required(VERSION 3.1) -> cmake_minimum_required(VERSION 3.5)
  - 原因：CMake 4.x 兼容性修复
  - 类型：平台适配

## 依赖版本

- CMake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

编译成功，生成了以下产物：
- libnitrokey.so (共享库)
- 头文件（include/libnitrokey/*.h）
- pkg-config 文件（lib/pkgconfig/libnitrokey-1.pc）
- udev 规则（rules.d/41-nitrokey.rules）

测试套件（unittest）需要 Nitrokey 硬件设备，无法在无硬件环境下运行。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnitrokey.so | 12M | 共享库 |
| NK_C_API.h | 36K | C API 头文件 |
| libnitrokey-1.pc | - | pkg-config 文件 |

## 注意事项

1. libnitrokey 是 Nitrokey 硬件密钥的通信库，需要硬件设备才能完整测试
2. 源码包含 hidapi 子模块，但使用内嵌版本，不需要外部依赖
3. CMake 识别为 HarmonyOS 平台（System is unknown to cmake），但不影响编译
4. /proc/meminfo 解析问题（鸿蒙平台）不影响编译
---

**编译结束**: 2026-06-10 16:59
**最终状态**: built
