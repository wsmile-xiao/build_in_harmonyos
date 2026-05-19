# mupdf-tools 1.27.2 适配笔记

## 编译环境
- 构建系统: makefile（自定义Makefile）
- 编译日期: 2026-05-18
- 编译器: clang/clang++
- 状态: built（成功）

## 编译步骤

MuPDF 使用自定义 Makefile 构建系统，不需要 configure 步骤。

### 1. 源码下载
使用 certifi 模块的证书路径手动下载，解决 SSL 证书验证问题。

### 2. 编译
```bash
make HAVE_X11=no HAVE_GLUT=no HAVE_CURL=no shared=no build=release \
    XCFLAGS="-DTOFU_CJK -DTOFU -DTOFU_NOTO -DTOFU_SIL -DFZ_ENABLE_HYPHEN=0" \
    HAVE_OBJCOPY=no
```

参数说明：
- `HAVE_X11=no`: 禁用 X11 GUI
- `HAVE_GLUT=no`: 禁用 GLUT GUI
- `HAVE_CURL=no`: 禁用网络功能
- `shared=no`: 编译静态库而非共享库
- `build=release`: 使用 release 构建
- `XCFLAGS="-DTOFU_CJK -DTOFU -DTOFU_NOTO -DTOFU_SIL -DFZ_ENABLE_HYPHEN=0"`: 禁用大型字体文件
- `HAVE_OBJCOPY=no`: 禁用 objcopy（避免生成大文件）

### 3. 安装
```bash
make DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX install-tools install-libs
install -m 755 build/release/muraster $DEFAULT_PREFIX/bin/muraster
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | Python SSL模块无法验证mupdf.com证书 | 使用certifi模块证书路径手动下载 |
| 2 | clang编译崩溃 | DroidSansFallback.ttf.c文件太大(约2MB C代码) | 使用DTOFU选项禁用大型字体文件 |
| 3 | muraster未自动安装 | muraster属于extra-apps而非标准tools | 手动install muraster到bin目录 |

## 源码修改

无补丁。编译参数调整解决所有问题。

## 依赖版本

MuPDF 内嵌所有依赖（thirdparty目录），无外部编译依赖：
- FreeType（内嵌）
- Harfbuzz（内嵌）
- libjpeg（内嵌）
- libpng（内嵌）
- OpenJPEG（内嵌）
- zlib（内嵌）
- jbig2dec（内嵌）
- lcms2（内嵌）

## 验证结果

```bash
# 版本验证
$DEFAULT_PREFIX/bin/mutool -v
mutool version 1.27.2

$DEFAULT_PREFIX/bin/muraster
muraster version 1.27.2

# 功能测试
$DEFAULT_PREFIX/bin/mutool info test.pdf     # PDF信息查询 ✅
$DEFAULT_PREFIX/bin/mutool draw -o out.png test.pdf  # PDF转PNG ✅
$DEFAULT_PREFIX/bin/mutool convert test.pdf  # PDF转换 ✅
$DEFAULT_PREFIX/bin/mutool pages test.pdf    # 页面信息 ✅
$DEFAULT_PREFIX/bin/mutool show test.pdf     # 内部结构 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mupdf-tools-1.27.2-ohos-aarch64.tar.gz | ~31MB | 预编译包 |
| mupdf-tools-1.27.2-ohos-aarch64-debug.tar.gz | ~48KB | 调试符号包 |

## 注意事项

1. **DTOFU选项说明**: 禁用大型字体文件不影响基本PDF解析，但可能影响某些特殊字体PDF的渲染效果
2. **无测试套件**: mupdf没有make test目标，需通过功能测试验证
3. **muraster手动安装**: extra-apps需要单独安装
4. **编译时间**: 因DTOFU选项，编译速度较快（约15分钟）

---

**编译结束**: 2026-05-18 15:35
**最终状态**: built（成功）