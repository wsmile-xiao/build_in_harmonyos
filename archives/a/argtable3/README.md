# argtable3

ANSI C 库，用于解析 GNU 风格的命令行选项。

## 简介

argtable3 是一个 ANSI C 库，提供简洁的声明式 API 来定义命令行参数，自动生成帮助信息和错误报告。它支持短选项（-h）、长选项（--help）、文件参数、整型参数、浮点参数、字符串参数、正则表达式参数、日期参数等多种类型。

## 官网

https://www.argtable.org

## 许可证

BSD-3-Clause

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 3.3.1 | published | 2026-05-28 | cmake | 2 |

### 补丁说明

| 补丁文件 | 说明 |
|----------|------|
| 0001-src-CMakeLists.txt.patch | 修复 cmake install 路径平台检测 + 移除 -Werror |
| 0002-tools-build.patch | 修复 shebang /bin/bash → /usr/bin/env bash |

### 已知平台问题

- cmake 不识别 HarmonyOS（CMAKE_SYSTEM_NAME 为 Unknown），需在 install 条件中添加 fallback
- HarmonyOS 无 /bin/bash，脚本 shebang 需用 /usr/bin/env bash
- -Werror 在新平台有编译风险

## 依赖

无外部依赖（纯 ANSI C 库）。