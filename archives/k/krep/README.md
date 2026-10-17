# krep

## 简介

krep 是 Davide Santangelo 开发的高性能文本搜索命令行工具。它使用 C 实现，支持 Boyer-Moore-Horspool、KMP、Two-Way、Shift-Or/BNDM、Aho-Corasick、POSIX ERE 正则、多线程搜索、递归目录过滤、JSON Lines 输出和上下文显示。

## OHOS 适配

- 使用 plain Makefile 构建系统，无 configure 脚本。
- `REG_STARTEND` 是 GNU 扩展，OHOS/musl regex 不支持，源码中增加条件编译保护。
- 构建环境缺少 `install` 工具时，Makefile 安装规则改为 `mkdir -p`、`cp`、`chmod`。
- 上游测试中硬编码 `/tmp`，在 OHOS 只读 `/tmp` 环境会失败，改为使用 `TMPDIR` 或当前工作目录。
- Conan 配方使用 clang、禁用架构探测相关默认优化，仅保留通用 C11/pthread/fPIC 编译参数。

## 依赖

- clang
- make
- pthread
- POSIX regex

## 功能验证

```bash
krep --version
krep needle file.txt
krep -c needle file.txt
```

## 参考

- 源码: https://github.com/davidesantangelo/krep
- Release: https://github.com/davidesantangelo/krep/releases/tag/v3.0.0
