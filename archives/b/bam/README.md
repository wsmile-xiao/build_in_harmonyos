# bam

> Lua-based build system for C/C++ projects

## 简介

bam 是一个基于 Lua 的构建系统，使用 Lua 脚本（bam.lua）来描述构建规则，可以编译 C/C++ 项目。版本 0.5.1 内置 Lua 5.3.3 源码（src/lua/ 目录），无需系统 Lua 依赖。

bam 提供简洁的 Lua API 来定义编译目标、依赖关系和构建规则，适合中小型 C/C++ 项目的构建管理。

## OHOS 适配要点

- **构建系统**：bam 使用自定义 Makefile + make_unix.sh，非 autotools/cmake。需要手动执行编译步骤。
- **内置 Lua**：Lua 5.3.3 源码包含在 src/lua/ 目录中，无需安装系统 Lua。
- **ELF 签名**：txt2c 工具（构建过程中生成）和 bam 二进制都需要 ELF 签名才能在 HarmonyOS 上执行。
- **系统链接器**：需要使用系统链接器 /data/service/hnp/bin/ld（OHOS SDK lld 缺少 libxml2.so.16）。

## 依赖

无外部依赖（Lua 5.3.3 源码内置）。

## 功能验证

```bash
bam --help
# 创建 bam.lua 项目并编译
bam
```

## 参考

- [bam GitHub 仓库](https://github.com/matricks/bam)
- [bam 文档](https://github.com/matricks/bam/tree/v0.5.1/docs)
