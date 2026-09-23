# Colibri Core

Colibri Core 是一个 C++ 文本处理库，用紧凑的二进制形式表示 n-gram、skipgram 和 flexgram，并提供语料编码、模式模型训练、检索和统计命令。

## 功能概述

- 类编码语料的编码与解码
- n-gram、skipgram 和 flexgram 数据结构
- 索引与非索引模式模型训练和查询
- BZip2 压缩流支持
- 7 个原生 C++ 命令和 10 个组合分析脚本

## HarmonyOS 适配

- 移除 Clang 下会无限递归的冗余 `PatternPointer` 转换运算符，保留等价转换构造函数。
- 修复 aarch64 上 `getopt()` 返回值被无符号 `char` 截断的问题。
- 上游测试在 `TMPDIR` 中运行，不依赖只读的 `/tmp`。
- Bash 脚本使用可移植的 `/usr/bin/env bash` shebang。
- 生成后的 Autotools 脚本兼容 HMFS/HMDFS 权限语义，并识别原生 HarmonyOS 三元组。
- 使用 Clang、libc++ 和静态 `libcolibricore.a` 构建。

## 依赖关系

- `bzip2/1.0.8`
- 构建工具：Autoconf、Automake、Libtool、Autoconf Archive

## 参考资料

- 官网：https://proycon.github.io/colibri-core/
- 源码：https://github.com/proycon/colibri-core
