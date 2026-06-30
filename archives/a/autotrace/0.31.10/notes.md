# autotrace 0.31.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**: 下载源码 tarball，解压到 ~/builds/autotrace-0.31.10.work
2. **Bootstrap**: 由于 autoreconf 失败（configure.ac 有语法问题），使用 hints/bootstrap.sh 复制预生成的 configure
3. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --without-magick --without-pstoedit --without-png`（LDFLAGS 由 configure.wrapper 自动设置）
4. **Make**: `make -j2`
5. **Install staging**: `make install DESTDIR=$TEST_PREFIX`
6. **Package**: 制作预编译包 autotrace-0.31.10-ohos-aarch64.tar.gz
7. **Install local**: `make install`（安装到 ~/usr/local）
8. **Verify**: 验证二进制可用性

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 intltool | 构建工具依赖 | 安装预编译包 intltool 0.51.0 |
| 2 | 缺少 gettext | 国际化库依赖 | 安装预编译包 gettext 0.22.5 |
| 3 | 缺少 glib-2.0 | 核心依赖库 | 安装预编译包 glib 2.88.0 |
| 4 | autoreconf 失败 | configure.ac 语法问题 | 使用 hints/bootstrap.sh + autotools-files 预生成配置 |
| 5 | glib 链接失败 | 静态库符号缺失 | configure.wrapper 设置 LDFLAGS 链接 libintl.a |
| 6 | 缺少 ImageMagick | 图像处理库可选 | 禁用 (--without-magick) |
| 7 | ELF 签名问题 | 鸿蒙系统要求 | 使用 ohc-run.py sign-elf 签名 |

## 源码修改

无源码补丁。使用 hints/bootstrap.sh + hints/autotools-files 提供预生成的 configure 和构建文件。

## 依赖版本

- glib 2.88.0
- gettext 0.22.5
- intltool 0.51.0
- pkg-config（系统）

## 验证结果

```bash
$ autotrace --version
AutoTrace version 0.40.0.

$ autotrace --help
Usage: autotrace [options] inputfile
Supported input formats: BMP, TGA, PBM, PGM, PPM
Supported output formats: ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| autotrace-0.31.10-ohos-aarch64.tar.gz | 3988KB | 预编译包（已 strip + 签名） |
| autotrace-0.31.10-ohos-aarch64-debug.tar.gz | 4132KB | Debug 符号包 |

## 注意事项

1. **功能限制**: 由于禁用了 Magick、PNG、pstoedit，图像处理功能受限，仅支持 BMP/TGA/PBM/PGM/PPM 格式
2. **Bootstrap 依赖**: 原始 tarball 没有 configure 脚本，需要使用 hints/bootstrap.sh + autotools-files
3. **版本显示**: 编译版本显示为 0.40.0（源码内部版本），与 tarball 标签 0.31.10 不一致
4. **LDFLAGS**: glib 静态库需要链接 libintl.a，configure.wrapper 已自动设置

---

**编译结束**: 2026-05-26 16:30
**最终状态**: built