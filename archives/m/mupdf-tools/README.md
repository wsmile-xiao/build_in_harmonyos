# mupdf-tools

## 软件描述

MuPDF 是一个轻量级的 PDF、XPS 和 EPUB 阅读器及渲染库。mupdf-tools 包含以下命令行工具：

- **mutool**: 多功能 PDF 工具，支持转换、提取、合并等操作
- **muraster**: PDF 到图像的转换工具

## 版本信息

- 当前版本: 1.27.2
- 官方主页: https://mupdf.com/

## 编译方法

MuPDF 使用自定义 Makefile 构建系统，不需要 configure 步骤。

```bash
# 编译命令（禁用 GUI 和大型字体以避免 clang 崩溃）
make HAVE_X11=no HAVE_GLUT=no HAVE_CURL=no shared=no build=release \
    XCFLAGS="-DTOFU_CJK -DTOFU -DTOFU_NOTO -DTOFU_SIL -DFZ_ENABLE_HYPHEN=0" \
    HAVE_OBJCOPY=no

# 安装
make DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX install-tools install-libs
install -m 755 build/release/muraster $DEFAULT_PREFIX/bin/muraster
```

## 依赖说明

MuPDF 内嵌了大多数依赖（第三方库）：
- FreeType (字体渲染)
- Harfbuzz (文本布局)
- libjpeg, libpng (图像处理)
- OpenJPEG (JPEG 2000)
- zlib (压缩)
- jbig2dec (JBIG2 解码)
- lcms2 (颜色管理)

无外部编译依赖。

## 已知问题

1. **clang 崩溃**: 编译大型嵌入式字体文件（如 DroidSansFallback.ttf.c）时 clang 可能崩溃
   - 解决方案: 使用 DTOFU 选项禁用大型字体

2. **无内置测试套件**: mupdf 没有 `make test` 目标，需手动验证工具可用性

3. **muraster 未自动安装**: 需要手动安装 muraster（它属于 extra-apps）

4. **JPEG输出不支持**: mutool draw 不支持直接输出JPEG格式

## 功能测试结果

| 功能 | 测试状态 |
|------|---------|
| mutool info (PDF信息) | ✅ 通过 |
| mutool draw (PDF转PNG) | ✅ 通过 |
| mutool convert (PDF转换) | ✅ 通过 |
| mutool pages (页面信息) | ✅ 通过 |
| mutool show (内部结构) | ✅ 通过 |
| muraster (光栅化) | ⚠️ 部分通过 |

## 编译版本

- 1.27.2 (2026-05-18) - built