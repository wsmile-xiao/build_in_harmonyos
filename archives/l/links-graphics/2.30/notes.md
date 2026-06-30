# links-graphics 2.30 — OpenHarmony 适配笔记

## 编译信息
- 软件: links-graphics 2.30
- 构建系统: autotools
- 编译器: clang (OpenHarmony SDK)
- 日期: 2026-06-04

## 遇到的问题及解决方式

### 问题 1: configure 中 FB 驱动检测要求 GPM
- **症状**: configure 检测 FB 驱动时，条件 `test "$cf_have_gpm" = yes` 要求 GPM (gpm.h/libgpm)，OpenHarmony 无此依赖
- **解决**: 移除 configure 和 configure.in 中 FB 驱动检测的 GPM 条件，使 FB 驱动可以仅依赖 Linux framebuffer API

### 问题 2: framebuf.c 直接引用 gpm.h 导致编译失败
- **症状**: `framebuf.c:31: #include <gpm.h>` 在无 GPM 系统上无法编译
- **解决**: 用 `#ifdef HAVE_LIBGPM` 守卫所有 GPM 相关代码：
  - `#include <gpm.h>` 和 `gpm_smooth` 宏定义
  - `fb_hgpm` 变量和 `fb_have_mouse` 宏（无 GPM 时仅检查 fb_hmice）
  - 整个 `fb_gpm_in()` 函数
  - `handle_fb_mouse()` 中 GPM 连接/打开代码
  - `unhandle_fb_mouse()` 中 GPM 关闭代码
  - PS/2 鼠标初始化错误处理（无 GPM 时直接失败而非 fall back 到 GPM）

## configure 选项
```
--prefix=/storage/Users/currentUser/usr/local --enable-graphics --with-ssl --with-fb --without-x --without-svgalib --without-directfb --without-atheos --without-haiku
```

## 动态库依赖
- libtiff.so, libjpeg.so, libpng16.so.16, libzstd.so.1, libssl.so.3, libcrypto.so.3, libomp.so, libc.so

## 安装的预编译依赖包
- openssl, zlib, bzip2, zstd, freetype2, fontconfig, libpng, libjpeg, libtiff, libwebp
---

**编译结束**: 2026-06-04 12:29
**最终状态**: built
