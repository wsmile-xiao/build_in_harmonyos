# Duktape — 嵌入式 JavaScript 引擎

## 简介

Duktape 是一个轻量级、可嵌入的 ECMAScript（JavaScript）引擎，专为 C/C++ 应用设计。它将完整的 JavaScript 运行时打包成一个单一的 C 源文件（`duktape.c`）和两个头文件（`duktape.h`、`duk_config.h`），便于集成到任何项目中。

- **官网**: https://duktape.org/
- **源码**: https://github.com/svaarala/duktape
- **许可证**: MIT
- **语言**: C
- **类别**: 实用工具类 — 嵌入式 JS 引擎

## 当前版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.7.0 | published | 2026-05-27 |

## 主要特性

- **单文件合并源码**: 整个引擎打包为 `duktape.c`，编译和集成极简
- **ECMAScript E5/E5.1 兼容**: 支持完整的 ES5.1 规范，部分 ES6 特性
- **极低资源占用**: 适合嵌入式和资源受限环境
- **C API 简洁**: 提供直观的 duk_xxx() API，无外部依赖
- **内置调试器**: 支持 Duktape 调试协议
- **模块化 extras**: 提供 print/alert、console.log、eventloop 等可选扩展

## 鸿蒙平台编译要点

### 构建系统

Duktape 不使用 autotools 或 cmake，而是提供多个专用 Makefile：
- `Makefile.sharedlibrary` — 构建共享库（libduktape.so）
- `src/duktape.c` — 合并单文件源码，可直接编译为静态库

### 编译命令

```bash
# 共享库
make -f Makefile.sharedlibrary CC=clang INSTALL_PREFIX=$DEFAULT_PREFIX CFLAGS="-fPIC -O2"

# 静态库（手动编译）
clang -O2 -fPIC -c src/duktape.c -Isrc -o duktape.o
llvm-ar rcs libduktape.a duktape.o

# duk 命令行工具（含 print/console 绑定）
clang -DDUK_CMDLINE_PRINTALERT_SUPPORT -DDUK_CMDLINE_CONSOLE_SUPPORT \
  -I./examples/cmdline -I./extras/print-alert -I./extras/console \
  -I$PREFIX/include -L$PREFIX/lib -Wall -Wextra -Os -o duk \
  ./examples/cmdline/duk_cmdline.c \
  ./extras/print-alert/duk_print_alert.c \
  ./extras/console/duk_console.c \
  -lduktape -lm
```

### 已知限制

- 默认配置不含 ES2015 Promise 支持（需自定义 duk_config.h）
- `duk` 命令行工具需编译 extras 才有 print()/console.log() 绑定
- 共享库 soname 版本采用 100×MAJOR + MINOR 约定（207 = 2.7）

## 依赖

无外部依赖。duktape 是纯 C 实现，仅依赖标准 C 库（libc + libm）。

## 交付物

| 文件 | 说明 |
|------|------|
| libduktape.a | 静态库（~600KB） |
| libduktape.so.207.20700 | 共享库（~355KB），soname=207 |
| duktape.h | 主头文件 |
| duk_config.h | 平台配置头文件 |
| duktape.pc | pkg-config 文件 |
| duk | 命令行解释器（~39KB） |