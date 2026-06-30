# kona

K 编程语言的开源实现——kona

kona 是 Arthur Whitney 设计的 K 编程语言的 C 语言开源实现。K 是一种面向数组的高级编程语言，
专为高性能数据处理和金融分析设计。kona 提供交互式解释器 `k`，支持数组运算、函数式编程范式。

## 基本信息

- **主页**: https://github.com/kevinlawler/kona
- **许可证**: ISC
- **语言**: C
- **构建系统**: 纯 Makefile
- **输出**: 单个二进制 `k`（解释器）
- **外部依赖**: 无（自包含项目）

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 20211225 | ✅ 已发布 | 2026-06-18 | Tag: Win64-20211225（跨平台 C 代码，非仅 Windows） |

## 构建说明

- **构建系统**: 纯 Makefile（非 autotools，无 configure 步骤）
- **编译器**: clang
- **编译参数**: `make CC=clang CFLAGS="-fPIC -O2" PRODFLAGS="-O3 -fPIC" PREFIX=$DEFAULT_PREFIX k`
- **平台适配**: Makefile 使用 `uname -s` 检测操作系统，HarmonyOS 返回 `harmonyos`，需添加对应 case
- **安装目标**: 已增加 DESTDIR 支持
