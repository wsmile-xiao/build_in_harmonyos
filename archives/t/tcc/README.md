# TCC (Tiny C Compiler)

## 简介

TCC 是一个小型、快速、无限制的 C 编译器。它可以直接编译并执行 C 代码，无需链接或汇编步骤。

## 主要特点

- **小型**: 约 100KB 的可执行文件（包括预处理器、编译器、汇编器和链接器）
- **快速**: 编译速度比 GCC 快约 9 倍
- **无限制**: 可以直接使用任何 C 动态库
- **C 脚本**: 支持 `#!/usr/local/bin/tcc -run` 直接执行 C 源代码

## OpenHarmony 适配

### 关键问题

1. **编译器选择**: OpenHarmony 系统无 gcc，必须使用 `--cc=clang`
2. **头文件路径**: 需指定 `--sysroot` 和 `--triplet=aarch64-linux-ohos`
3. **运行时库**: libtcc1.a 需用 clang 编译（`arm64-libtcc1-usegcc=yes`）
4. **ELF 签名**: 所有可执行文件必须签名才能执行

### Configure 参数

```bash
./configure --prefix=$HOME/usr/local --cc=clang \
  --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
  --triplet=aarch64-linux-ohos
```

## 使用限制

- tcc 本身需要 ELF 签名才能运行 ✅ 已完成
- tcc 编译出的程序也需要 ELF 签名才能执行 ⚠️ 用户需手动签名
- 不支持所有 GCC/Clang 扩展属性（如 `__attribute__((__availability__...))`）

## 支持平台

TCC 支持多种架构：i386, x86_64, arm, arm64, riscv64

## 参考资料

- 官网: https://bellard.org/tcc/
- Git Repository: https://repo.or.cz/w/tinycc.git
- 文档: tcc-doc.html（源码包内）