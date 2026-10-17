# cc65 2.19 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-29
- 包类型: 命令行工具（6502 交叉编译器套件，包含 cc65/ca65/cl65/ld65 等可执行文件）
- 编译器: clang（来自 ohos-aarch64 profile）
- 状态: built

## 概述

cc65 是一套面向 6502 系列 CPU 的 C 编译器开发套件。产出的工具
（cc65/ca65/cl65/ld65/ar65/da65/od65/grc65/chrcvt65/sim65/sp65）
运行于 HarmonyOS PC (aarch64) 宿主，生成 6502 目标代码；不在宿主执行 6502 代码。

## 依赖
- 无外部依赖，自包含构建

## 编译步骤

```bash
# 获取编译器（R33: 从 Conan conf 获取，不使用 shell 环境变量）
CC=/data/service/hnp/bin/clang
AR=llvm-ar

# 仅构建 src/ 目录（编译器工具链）
# libsrc/ 需运行刚构建的 cc65 工具编译 6502 目标库，交叉编译环境跳过
# doc/ 需 texinfo，跳过
# samples/ 需运行 cc65 工具，跳过
make -C src bin CC=$CC AR=$AR -j1

# 安装到 Conan 包目录
make -C src install PREFIX=$PACKAGE_FOLDER
```

## 构建范围

仅构建核心编译器工具组件（src/ 目录）：
- cc65（C 编译器）
- ca65（宏汇编器）
- cl65（编译驱动器）
- ld65（链接器）
- ar65（归档工具）
- co65（目标文件转换器）
- da65（反汇编器）
- od65（目标文件转储工具）
- grc65（GEOS 资源编译器）
- chrcvt65（字符集转换工具）
- sim65（6502 模拟器）
- sp65（sprite/图片转换工具）

未构建的组件：
- libsrc（6502 目标库，需运行 cc65 工具，交叉编译环境跳过）
- doc（文档，需 texinfo）
- samples（示例，需运行 cc65 工具）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 默认使用 gcc | `CC = $(CROSS_COMPILE)gcc` | 通过 `make CC={conan_cc}` 覆盖（R33） |
| 2 | libsrc 构建失败 | 需运行刚构建的 cc65 工具编译 6502 目标库 | 仅构建 src/ 目录，跳过 libsrc/ |

## 源码下载
- 官方源: https://github.com/cc65/cc65/archive/refs/tags/V2.19.tar.gz
- SHA256: 157b8051aed7f534e5093471e734e7a95e509c577324099c3c81324ed9d0de77

## 测试说明
cc65 上游提供 test/ 目录测试套件（compile 和 util），但需运行 cc65 二进制，
交叉编译环境可能无法执行 aarch64 二进制，故 test_package 通过 cross_building 检测并跳过。

test_package 验证内容：
- `cc65 --version`：验证编译器二进制可执行
- `ca65 --version`：验证汇编器二进制可执行
- `cl65 --version`：验证驱动器二进制可执行
- `cc65 -c test.c`：验证编译器可编译 C 代码为 6502 汇编（R34）
- `test -f test.s`：验证汇编输出文件生成

## 验证结果
- `cc65 --version` 预期输出版本号 V2.19
- `cc65 -c test.c` 预期生成 test.s 汇编文件
- 交叉编译环境下 test_package 跳过（cross_building 检测）

## 注意事项
- 仅构建编译器工具组件，libsrc（目标库）未构建，cl65 链接功能不可用
- 目标库可在目标设备上使用 `make -C libsrc` 单独构建
- 无需补丁，Makefile 支持通过命令行变量覆盖 CC/AR

---

**编译结束**: 2026-07-29
**最终状态**: built
