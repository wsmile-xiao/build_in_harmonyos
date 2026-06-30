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

### 适配要点

1. **构建系统**：使用 CMake 构建
2. **依赖处理**：需要设置 `ZLIB_ROOT` 环境变量指向 zlib 安装路径
3. **pkg-config**：需要设置 `PKG_CONFIG_PATH` 包含 zlib.pc 所在路径
4. **纯静态库**：该软件编译为纯静态库（libxlsxwriter.a），无可执行二进制文件
5. **构建选项**：
   - `-DBUILD_TESTS=OFF` 关闭测试编译
   - `-DBUILD_EXAMPLES=OFF` 关闭示例编译

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