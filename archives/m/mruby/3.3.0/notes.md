# mruby 3.3.0 适配笔记

## 编译环境
- 构建系统: rake (Ruby 构建系统，非 autotools/meson)
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

mruby 使用 rake 构建系统（非 autotools/meson），需要自定义 build_config.rb。

1. 创建 `build_config/ohos.rb` 配置文件（使用 clang 工具链，设置 CC/linker/archiver）
2. 设置环境变量: `CC=clang`, `CXX=clang++`, `AR=llvm-ar`, `CFLAGS="-fPIC -O2 -Wall"`
3. 编译: `rake MRUBY_CONFIG=ohos`
4. 安装 (DESTDIR): `PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX rake MRUBY_CONFIG=ohos install`
5. 安装 (本地): `PREFIX=$DEFAULT_PREFIX rake MRUBY_CONFIG=ohos install`
6. 测试: `rake MRUBY_CONFIG=ohos test`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | GitHub HTTPS 验证失败 | curl -L 手动下载 tar.gz |
| 2 | ld.lld 找不到 -lm | OpenHarmony 无独立 libm | build_config 中 linker.libraries = %w() |
| 3 | ld.lld 找不到 libc 函数 | 环境变量 LD=ld.lld 覆盖了 clang linker | build_config 中 linker.command = 'clang' |
| 4 | 测试失败 (Dir, UNIXSocket) | /tmp 只读(E002)，UNIX socket bind() 未实现(E051) | 记录为平台限制，不影响运行时功能 |

## 源码修改

新增文件 `build_config/ohos.rb`:
- 使用 clang toolchain
- CC = clang, linker.command = clang, AR = llvm-ar
- linker.libraries = %w() (OpenHarmony libc 包含 math)
- gembox 'default' (包含完整 mruby 功能集)
- enable_test, enable_bintest

## 依赖版本

- Ruby 3.4.5 (构建工具)
- rake 13.2.1 (构建工具)
- clang 15.0.4 (编译器)
- llvm-ar (归档器)
- 无第三方库依赖 (mruby 是自包含的轻量级 Ruby 实现)

## 验证结果

```bash
$ mruby --version
mruby 3.3.0 (2024-02-14)
$ mrbc --version
mruby 3.3.0 (2024-02-14)
$ mruby-strip --help
Usage: .../mruby-strip [switches] irepfiles
$ mirb --version
mruby 3.3.0 (2024-02-14)
$ mrdb --version (交互式调试器)
```

测试结果: 1574/1606 OK (98%), 失败项均为 OpenHarmony 平台限制。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mruby-3.3.0-ohos-aarch64.tar.gz | 8555KB | 预编译包 (bin + lib + include) |

## 注意事项

1. mruby 不使用 autotools/meson，使用 rake 构建系统
2. 环境变量 LD=ld.lld 会覆盖 CC=clang 作为 linker，需要在 build_config 中显式设置 linker.command = 'clang'
3. OpenHarmony 无独立 libm，需要设置 linker.libraries = %w()
4. rake install 使用 DESTDIR 环境变量 (不是 make DESTDIR=)
5. rake install 使用 PREFIX/INSTALL_PREFIX 环境变量设置安装前缀
---

**编译结束**: 2026-08-07 00:45
**最终状态**: built
