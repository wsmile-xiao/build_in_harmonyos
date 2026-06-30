# yasm

**描述**: Yasm 是一个模块化、可重用的汇编器，支持多种汇编语法（NASM、GAS、TASM 等）

**版本**: 1.3.0-r4

**主页**: https://yasm.tortall.net/

**编译状态**: published ✅

## 支持的架构

- x86 (32-bit)
- x86-64 (AMD64)
- LC3B (简化版)

## 编译说明

yasm 在 HarmonyOS 上编译时遇到 re2c 工具崩溃问题，使用简化版 token lexer 替代。

## 依赖

无外部依赖，动态链接 musl。

## 安装

```bash
tar xzf yasm-1.3.0-r4-ohos-aarch64.tar.gz
cd yasm-1.3.0-r4
./install.sh
```

## 使用示例

```bash
# 汇编 NASM 文件
yasm -f elf64 -o output.o input.asm

# 查看支持的格式
yasm --help
```

## 功能限制

由于 re2c 工具在 HarmonyOS 上存在内存分配问题，GAS/NASM 解析器使用简化实现，可能影响完整功能。