# base16384

base16384 是一个纯 C 实现的编码库，将二进制数据编码为 UTF-16BE 格式的 CJK 汉字（使用 2^14 = 16384 个汉字作为字母表）。

## 功能概述

- 将任意二进制数据编码为可打印的 CJK 汉字序列
- 支持文件、fd、FILE*、流等多种 IO 接口
- 支持编码/解码的 safe/unsafe/标准三种变体
- 内置校验和验证（可选）
- 零外部依赖，纯 C 标准库

## OHOS 适配

- 构建系统为 cmake，需要 1 个补丁（CMake minimum version 适配）
- 无外部依赖

## 依赖关系

- C 编译器（clang）

## 参考资料

- 源码: https://github.com/fumiama/base16384
- 许可证: GPL-3.0-or-later
