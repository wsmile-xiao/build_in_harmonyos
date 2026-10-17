# asciiTeX — ASCII 方程渲染器

asciiTeX 是一个将 LaTeX 数学公式渲染为 ASCII 艺术文本的命令行工具。它支持分数、根号、上下标、矩阵、极限等多种数学表达形式，输出为纯文本 ASCII 字符绘制的公式，适合在终端或纯文本环境中展示数学公式。

## 功能概述

- 将 LaTeX 数学表达式渲染为 ASCII 艺术格式
- 支持分数 (\frac)、根号 (\sqrt)、上下标 (^{}/_{})
- 支持二项式系数 (\binom)、极限 (\lim)、求和/积分符号
- 支持矩阵/数组 (\array)、花括号/方括号分组
- 命令行直接传入方程或从文件读取 (-f)
- 可指定输出行宽 (-ll)

## OHOS 适配要点

- **CMake 版本兼容**：CMakeLists.txt 使用 `cmake_minimum_required(VERSION 3.0)`，在 CMake 4.x 上需设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- **链接器问题**：OHOS 默认 lld 有 libxml2.so.16 依赖问题，conanfile.py 中通过 `shutil.which("ld")` 动态检测 GNU ld
- **构建时测试**：CMake POST_BUILD 命令在构建时执行二进制，OHOS 上未签名 ELF 无法执行，设置 `DISABLE_TESTING=ON`
- **无外部依赖**：纯 C 项目，自包含，无需任何外部库

## 依赖关系

### 编译依赖
- 无（纯 C，自包含）

### 运行依赖
- libc.so（系统 libc）
- libdl.so（动态链接器）

## 参考资料

- 官网：http://asciitex.sourceforge.net/
- 源码：https://github.com/larseggert/asciiTeX
- 许可证：GPL-2.0
- 作者：Lars Eggert (fork), Bart Pieters (fork), Przemek Borys (original, eqascii)
