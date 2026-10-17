# imagemagick-full 7.1.2-23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. `init-build imagemagick-full 7.1.2-23 --url=...`
2. 应用 autotools OHOS triplet 补丁 (`patch-autotools-ohos.pl config/config.guess config/config.sub`)
3. 修补 HMDFS 权限问题：将 configure/config.status 中 `umask 077` 改为 `umask 022`
4. `umask 022 && ./configure --prefix=$DEFAULT_PREFIX --enable-shared --with-jpeg --with-png --with-tiff --with-freetype --with-fontconfig --with-openjp2 --without-webp --without-heic --without-xml --disable-openmp`
5. `make -j2 && make install DESTDIR=$TEST_PREFIX && make install`
6. 验证 `$DEFAULT_PREFIX/bin/magick --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess/config.sub 不识别 OHOS triplet | 缺少 __OHOS__/ohos-linux 检测 | patch-autotools-ohos.pl 打补丁 |
| E050a | config.status 创建临时目录 Permission denied | HMDFS 上 umask 077 创建目录权限 0700，目录 owner 继承父目录 uid (20001006)，当前用户 uid (20020101) 不匹配，无法写入 | 将 configure/config.status 中 `umask 077` 改为 `umask 022` |
| E050b | `rm -rf conf*` 匹配 config/ 和 configure 导致误删 | glob `conf*` 匹配 config/ 目录和 configure 文件 | 删除时使用精确路径，避免 glob 匹配 |
| 无 | webp/heic/xml 无预编译包 | 无对应 OHOS aarch64 预编译依赖 | configure 时禁用 --without-webp --without-heic --without-xml |

## 源码修改

- `config/config.guess`: OHOS triplet 检测 (__OHOS__, HarmonyOS)
- `config/config.sub`: ohos-linux triplet 支持
- `configure`: umask 077 → umask 022 (2处)
- `config.status`: umask 077 → umask 022 (2处)

## 依赖版本

| 依赖 | 版本 |
|------|------|
| libjpeg (turbo) | 4.1.1 |
| libpng16 | 1.6.43 |
| libtiff-4 | 4.6.0 |
| freetype2 | 26.20.6 |
| fontconfig | 2.16.0 |
| libopenjp2 | 2.5.0 |
| clang | 15.0.4 |

## 验证结果

```bash
$ magick --version
Version: ImageMagick 7.1.2-23 Q16-HDRI aarch64 6c51b2de5:20260516 https://imagemagick.org
Copyright: (C) 1999 ImageMagick Studio LLC
License: https://imagemagick.org/license/
Features: Cipher DPC HDRI
Delegates (built-in): djvu fontconfig freetype jp2 jpeg lcms lzma tiff zlib zstd
Compiler: clang (15.0.4)
```

## 交付物

| 文件 | 说明 |
|------|------|
| imagemagick-full-7.1.2-23-ohos-aarch64.tar.gz | 预编译包 |
| aarch64-debug.tar.gz | debug 信息包 |

## 注意事项

- HMDFS 上 config.status 创建临时目录会继承父目录 owner（非当前 uid），需将 umask 077 改为 umask 022 才能写入
- 清理 conf* 时避免使用 glob 模式，应使用精确路径防止误删 config/ 目录
- 无 webp/heic/xml 预编译依赖，需要时需先编译这些库
---

**编译结束**: 2026-08-07 02:11
**最终状态**: built
