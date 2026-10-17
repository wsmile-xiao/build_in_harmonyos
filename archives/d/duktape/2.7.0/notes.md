# duktape 2.7.0 适配笔记

## 编译环境
- 构建系统: makefile (Makefile.sharedlibrary)
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

duktape 使用自定义 Makefile 构建系统，不是标准的 autotools。提供 `Makefile.sharedlibrary` 来构建共享库。

1. 使用 `Makefile.sharedlibrary` 构建共享库：
   ```bash
   make -f Makefile.sharedlibrary CC=clang INSTALL_PREFIX=$DEFAULT_PREFIX CFLAGS="-fPIC -O2"
   ```

2. 手动构建静态库：
   ```bash
   clang -O2 -fPIC -c src/duktape.c -Isrc -o duktape.o
   llvm-ar rcs libduktape.a duktape.o
   llvm-ranlib libduktape.a
   ```

3. 安装到 staging (DESTDIR 模式)：
   ```bash
   make -f Makefile.sharedlibrary install CC=clang INSTALL_PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
   cp libduktape.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
   ```

4. 构建 duk 命令行工具（含 print/alert 和 console 支持）：
   ```bash
   clang -DDUK_CMDLINE_PRINTALERT_SUPPORT -DDUK_CMDLINE_CONSOLE_SUPPORT \
     -I./examples/cmdline -I./extras/print-alert -I./extras/console \
     -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib \
     -Wall -Wextra -Os -o duk \
     ./examples/cmdline/duk_cmdline.c \
     ./extras/print-alert/duk_print_alert.c \
     ./extras/console/duk_console.c \
     -lduktape -lm
   ```

5. 安装 duk 到 staging 和 DEFAULT_PREFIX：
   ```bash
   cp duk $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   cp duk $DEFAULT_PREFIX/bin/
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 错误提升 debugger 子目录为源码根 | duktape tarball 含 debugger 子目录，init-build 的嵌套源码检测误判 | 手动重新解压 tarball，正确设置 .orig 和 .work 目录 |
| 2 | SSL 下载失败 | 鸿蒙环境 SSL 证书验证失败 | 使用 curl -L -k 手动下载 |

## 源码修改

无源码修改，未生成补丁。

## 依赖版本

无外部依赖。

## 验证结果

```bash
$DEFAULT_PREFIX/bin/duk -e "print('Duktape version: ' + Duktape.version);"
Duktape version: 20700
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libduktape.a | ~600KB | 静态库 |
| libduktape.so.207.20700 | ~355KB | 共享库 |
| duk | ~39KB | 命令行解释器 |
| duktape.h | ~75KB | 头文件 |
| duk_config.h | ~127KB | 配置头文件 |
| duktape.pc | ~240B | pkg-config 文件 |

## 注意事项

- duktape 不使用标准 autotools/configure，构建系统为 makefile (Makefile.sharedlibrary)
- duk 命令行工具需要编译 extras (print-alert, console) 才能获得 print/console.log 等绑定
- 共享库 soname 版本为 207 (基于 100*MAJOR + MINOR 约定)
---

**编译结束**: 2026-07-15 15:27
**最终状态**: built
