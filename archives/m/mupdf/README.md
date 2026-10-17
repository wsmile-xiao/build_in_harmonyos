# mupdf

MuPDF 是一个轻量级的 PDF、XPS 和电子书查看器及工具包。

## 描述

MuPDF 是由 Artifex Software 开发的开源 PDF 渲染引擎，专注于速度和代码质量。它提供高质量的 PDF 渲染、文本提取和文档转换功能。

## 已编译版本

| Version | Status | Date |
|---------|--------|------|
| 1.25.1  | built  | 2026-09-17 |
| 1.27.2  | built  | 2026-05-25 |

## 构建说明

> 以下构建说明针对 **1.27.2**（系统库方案）。**1.25.1** 采用全内嵌 thirdparty 子模块
> 方案（14 个子模块按 tag 精确 commit 下载、零外部 conan 依赖、不裁剪功能），
> 详见 `1.25.1/notes.md`。

- 构建系统：GNU Makefile
- 构建命令：`make USE_SYSTEM_LIBS=yes USE_SYSTEM_LCMS2=yes USE_SYSTEM_BROTLI=yes mujs=no html=no extract=no HAVE_GLUT=no HAVE_X11=no HAVE_OBJCOPY=no HAVE_LIBCRYPTO=yes`
- 补丁数：6（mujs 子模块源码填充）
- 禁用特性：JS引擎(mujs=no)、HTML引擎(html=no)、EPUB/FB2/MOBI等格式

## 关键适配问题

1. **mujs 子模块为空**：tarball 中 mujs 为 git submodule 引用但源码缺失，需手动填充 regexp/utf 相关文件
2. **ld.lld 不支持 -b binary**：设置 HAVE_OBJCOPY=no 使用 hexdump 方法嵌入字体
3. **gumbo-parser 无预编译包**：禁用 HTML 支持 (html=no)
4. **jbig2dec 无 cmd-pkgs**：手动从源码编译 jbig2dec 0.20
5. **HMDFS 无 GNU install**：使用 busybox install 替代

## 依赖

| Dependency | Version | Source |
|-----------|---------|--------|
| freetype | 2.13.3 | cmd-pkgs |
| libjpeg-turbo | 3.1.0 | cmd-pkgs |
| zlib | 1.2.13 | system |
| openjpeg | 2.5.0 | cmd-pkgs |
| libpng | 1.6.44 | cmd-pkgs |
| lcms2 | 2.16 | cmd-pkgs |
| brotli | 1.1.0 | cmd-pkgs |
| jbig2dec | 0.20 | manual compile |
| openssl | 3.4.1 | cmd-pkgs |

## 构建产物

- libmupdf.a (52 MB) - 静态库
- libmupdf-pkcs7.a (25 KB) - PKCS7 模块
- libmupdf-threads.a (5.7 KB) - 线程模块
- mutool (36 MB) - 命令行工具

## 使用方法

```bash
# 查看版本
mutool -v
# Output: mutool version 1.27.2

# 转换 PDF 为图片
mutool convert -o output.png input.pdf

# 提取文本
mutool draw -F text input.pdf
```