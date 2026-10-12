# libxlsxwriter

## 简介

libxlsxwriter 是一个 C 库，用于创建 Microsoft Excel 2007+ 的 XLSX 文件。它提供了完整的 API 来写入文本、数字、公式、超链接、图片、图表等 Excel 元素。

## 功能概述

- 创建 XLSX 格式 Excel 文件
- 支持多工作表（Worksheet）
- 支持格式化单元格（字体、颜色、边框等）
- 支持写入公式
- 支持图表（Chart）
- 支持图片插入
- 支持超链接
- 高性能，适合大数据量写入

## OHOS 适配

### 适配要点（2026-09-22 conan 配方版）

1. **构建系统**：CMake（≥3.16，配方加 CMAKE_POLICY_VERSION_MINIMUM=3.5）
2. **依赖处理**：zlib 为唯一外部依赖（conan zlib/1.3.1.1）；minizip/tmpfileplus/md5 全部 vendored 静态编入库（上游默认）
3. **ZLIB 发现**：上游用 MODULE 模式 find_package(ZLIB)，配方预置 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY 缓存变量（conan zlib 真实路径）绕交叉链 FIND_ROOT_PATH=ONLY
4. **纯静态库**：libxlsxwriter.a，无可执行产物
5. **上游测试真跑**：unit 420/420（ctest.h 框架）+ functional 791 用例金标比对（793 exe，747 .xlsx golden）+ 消费者冒烟
6. **关键坑**：OHOS toolchain 链接默认 -Wl,--gc-sections 会回收 .ctest 测试注册段（unit 显示 0 tests）——需 -DCMAKE_EXE_LINKER_FLAGS=-Wl,--no-gc-sections

### 已知问题

无已知问题，编译过程顺利。

## 排除与替代

无。

## 依赖

### 编译依赖
- zlib 1.2.8+（必需）

### 运行依赖
- 无（静态库编译后无运行依赖）

## 功能验证

作为纯静态库，无独立可执行文件。验证方式：
1. 检查 `libxlsxwriter.a` 是否存在
2. 检查头文件 `xlsxwriter.h` 是否安装
3. 编写测试程序链接该库并生成 XLSX 文件

## 参考

- 官网：https://libxlsxwriter.github.io/
- 源码：https://github.com/jmcnamara/libxlsxwriter
- 文档：https://libxlsxwriter.github.io/using_libxlsxwriter.html