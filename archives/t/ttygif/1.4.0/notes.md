# ttygif 1.4.0 适配笔记

## 编译环境
- 构建系统: makefile（纯Makefile，无configure脚本）
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

ttygif 是一个简单的纯 Makefile 项目，没有 configure 脚本。编译命令：
```bash
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-fPIC -O2 -Wall -DVERSION='\"1.4.0\"'" PREFIX=$DEFAULT_PREFIX
make install CC=clang CFLAGS="-fPIC -O2 -Wall -DVERSION='\"1.4.0\"'" PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile无DESTDIR支持 | 原始Makefile install目标直接用$(PREFIX)/bin，不支持DESTDIR staging隔离 | 修改Makefile install目标：$(PREFIX)/bin → $(DESTDIR)$(PREFIX)/bin |
| 2 | ttygif.c硬编码/tmp路径 | ttygif.c第297行 `char dir_template[] = "/tmp/ttygif.XXXXXX"` 硬编码/tmp，违反R10铁律 | 改为先读取TMPDIR环境变量，回退/tmp；动态拼接路径 |
| 3 | Makefile使用gcc | 原始Makefile `CC = gcc`，鸿蒙平台使用clang | 通过make命令行参数 `CC=clang` 覆盖 |
| 4 | manifest缺少build_system顶层字段 | G4门禁检查顶层`build_system:`字段，但manifest模板中该字段在`build.system:`下 | 在manifest.yaml顶层添加 `build_system: makefile` |
| 5 | ImageMagick库加载问题 | convert命令依赖的libMagickCore等库加载失败 | ttygif编译本身不依赖ImageMagick库（仅运行时调用convert命令），编译不受影响 |

## 源码修改

两个文件被修改：

1. **Makefile** - 添加DESTDIR支持
   - `mkdir -p $(PREFIX)/bin` → `mkdir -p $(DESTDIR)$(PREFIX)/bin`
   - `cp ttygif $(PREFIX)/bin/ttygif` → `cp ttygif $(DESTDIR)$(PREFIX)/bin/ttygif`

2. **ttygif.c** - 修复硬编码/tmp（R10铁律）
   - 将 `char dir_template[] = "/tmp/ttygif.XXXXXX"` 改为动态读取TMPDIR环境变量
   - 使用sprintf拼接路径：`sprintf(dir_template, "%s/ttygif.XXXXXX", tmpdir_env)`

## 依赖版本

- ImageMagick: 7.x（运行时依赖，编译不需要）

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/ttygif --version
1.4.0

$ $DEFAULT_PREFIX/bin/ttygif -h
Usage: ttygif [FILE]
  -h, --help : print this help
  -v, --version : print version
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ttygif-1.4.0-ohos-aarch64.tar.gz | ~90KB | 预编译包（release） |
| ttygif-1.4.0-ohos-aarch64-debug.tar.gz | ~41KB | 预编译包（debug） |

## 注意事项

- ttygif运行时依赖ImageMagick的convert命令，当前环境中convert有库加载问题，可能需要修复ImageMagick的库路径
- ttygif使用xwd（Linux）或screencapture（macOS）截屏，在鸿蒙环境中需要适配截屏方案
- 无configure脚本，所有编译参数通过make命令行传递
---

**编译结束**: 2026-05-29 11:02
**最终状态**: built
