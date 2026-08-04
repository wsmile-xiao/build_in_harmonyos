# pcalc — 程序员命令行计算器

## 简介

pcalc 是一个面向程序员的命令行计算器，支持十六进制（0x）、十进制、八进制（0c/0o）、二进制（0y）的混合运算。纯 C 语言编写，依赖极少，适合嵌入式和系统级开发环境。

## 主要特性

- **多进制混合运算**：在同一表达式中混合使用 hex/dec/oct/bin
- **位运算支持**：AND、OR、XOR、NOT、移位等
- **C 风格语法**：支持三元运算符、类型转换
- **轻量级**：仅依赖 flex/bison，无外部库依赖

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| flex | 构建工具 | 词法分析器生成 |
| bison | 构建工具 | 语法分析器生成 |

## 构建系统

- **类型**：Makefile（无 configure 脚本）
- **构建命令**：`make`
- **安装命令**：`make install`

## OHOS 适配要点

1. **工具类型**：pcalc 是可执行文件，不是库
2. **构建依赖**：需要 flex 和 bison 作为 tool_requires
3. **静态链接**：OHOS 上使用 LDFLAGS=-static 避免运行时链接问题
4. **无运行时依赖**：独立运行，无需额外库

## 功能验证

```bash
# 基本计算
pcalc 1+1

# 十六进制运算
pcalc 0xFF + 1

# 二进制运算
pcalc 0y1010 & 0y1100

# 位移运算
pcalc 255 >> 4
```

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.0.0 | pending | 首个 OHOS 适配版本 |

## 许可证

GPL-2.0（详见 COPYING 文件）

## 参考

- 官网: https://github.com/vapier/pcalc
- 源码: https://github.com/vapier/pcalc/archive/refs/tags/v3.tar.gz
