# 适配笔记 — graphite2 1.3.14

## 基本信息
- 软件: graphite2
- 版本: 1.3.14
- 上游: https://github.com/silnrsi/graphite
- 构建系统: CMake (非 autotools)
- 许可证: LGPL-2.1-or-later / MPL-1.1 / GPL-2.0-or-later

## 构建配置
- 静态编译: `-DBUILD_SHARED_LIBS=OFF` (R5/R26)
- 构建类型: Release
- 无外部 C 依赖 (纯 C/C++ 库)
- CMake 策略: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` (兼容 CMake 4.x)

## 遇到的问题

### 1. CMake 4.x 兼容性
- **问题**: CMakeLists.txt 中 `CMAKE_MINIMUM_REQUIRED(VERSION 2.8.0)` 在 CMake 4.x 中报错
- **原因**: CMake 4.x 移除了对 < 3.5 的兼容性支持
- **解决**: 在 conanfile.py 的 `generate()` 中设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`

### 2. -Wno-class-memaccess 警告
- **问题**: clang 不识别 `-Wno-class-memaccess` (GCC 专有编译标志)
- **影响**: 仅产生警告，不影响编译
- **解决**: 无需处理，非阻塞警告

### 3. Python 找包警告
- **问题**: CMP0148 策略警告 (find_package(PythonInterp) 已废弃)
- **影响**: 仅警告，不影响构建

## 测试结果
- 83/83 测试通过 (ctest --output-on-failure)
- 总耗时: 2.63 秒
- 所有测试: bittwiddling, endian, featuremap, grlist, json, nametable, sparse, utf, vm (call+direct), examples (simple, features, clusters, linebreak)

## 产物
- libgraphite2.a (静态库)
- include/graphite2/Font.h, Segment.h, Types.h, Log.h
- bin/gr2fonttest (字体测试工具)
- lib/pkgconfig/graphite2.pc
- share/graphite2/graphite2.cmake (CMake 包配置)
---

**编译结束**: 2026-07-22 10:20
**最终状态**: built
