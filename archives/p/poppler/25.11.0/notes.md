# Poppler 25.11.0 编译笔记

## 基本信息
- 软件: poppler
- 版本: 25.11.0
- 构建系统: cmake
- C++ 标准: C++20（需要补丁兼容 Clang 15）
- 状态: built

## 编译环境

| 项目 | 值 |
|------|-----|
| 编译器 | Clang 15.0.4 |
| cmake 版本 | 4.1.2 |
| 安装前缀 | /storage/Users/currentUser/usr/local |
| 平台 | OpenHarmony (HarmonyOS Kernel 1.12.0) |

## 编译步骤

### 1. init-build
```bash
python3 scripts/ohc-run.py init-build poppler 25.11.0 --url=https://poppler.freedesktop.org/poppler-25.11.0.tar.xz
```

### 2. cmake 配置
```bash
cd ~/tmp/builds/poppler-25.11.0.work/build
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_PREFIX_PATH=/storage/Users/currentUser/usr/local \
  -DIconv_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include \
  -DIconv_LIBRARY=/storage/Users/currentUser/usr/local/lib/libiconv.so \
  -DENABLE_NSS3=OFF \
  -DENABLE_GPGME=OFF \
  -DENABLE_BOOST=OFF \
  -DENABLE_GLIB=OFF \
  -DENABLE_QT5=OFF \
  -DENABLE_QT6=OFF \
  ..
```

### 3. 编译
```bash
make -j4
```

### 4. staging 安装
```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-poppler-25.11.0
```

### 5. finish
```bash
python3 scripts/ohc-run.py finish poppler 25.11.0 built
```

## 遇到的问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| cmake 找不到 Iconv | libiconv 没有 .pc 文件 | 显式指定 `-DIconv_INCLUDE_DIR` 和 `-DIconv_LIBRARY` |
| `std::ranges::sort` 未定义 | Clang 15 不完全支持 C++20 ranges | 替换为 `std::sort(container.begin(), container.end())` |
| `std::ranges::find` 未定义 | 同上 | 替换为 `std::find(container.begin(), container.end())` |
| `std::ranges::reverse_view` 未定义 | 同上 | 使用 `rbegin()/rend()` 反向迭代器 |
| C 数组调用 `.begin()` | C 数组没有成员函数 | 使用 `std::begin(arr)` 和 `std::end(arr)` |
| 缺少 libiconv.so 符号链接 | 预编译包只安装了版本化库 | 手动创建符号链接 |

## 源码修改

共修改 17 个文件，生成 17 个补丁：

1. `cpp/poppler-document.cpp` - std::ranges::copy → std::copy
2. `cpp/poppler-image.cpp` - std::ranges::transform → std::transform
3. `fofi/FoFiTrueType.cc` - std::ranges::sort → std::sort
4. `poppler/Annot.cc` - std::ranges::find → std::find
5. `poppler/CIDFontsWidthsBuilder.h` - std::ranges::find_if + reverse_view → std::find_if(rbegin, rend)
6. `poppler/Catalog.cc` - std::ranges::sort/lower_bound → std::sort/lower_bound
7. `poppler/Dict.cc` - std::ranges::sort/lower_bound → std::sort + 自定义比较器
8. `poppler/Gfx.cc` - std::ranges::sort + C 数组 → std::sort(std::begin, std::end)
9. `poppler/GfxFont.cc` - std::ranges::sort/any_of → std::sort/std::any_of
10. `poppler/GlobalParams.cc` - std::ranges::find/replace → std::find/std::replace
11. `poppler/PDFDoc.cc` - std::ranges::find → std::find
12. `poppler/TextOutputDev.cc` - std::ranges::sort/reverse/transform → std::sort/reverse/transform
13. `splash/SplashClip.cc` - std::ranges::all_of → std::all_of
14. `splash/SplashFontEngine.cc` - std::ranges::fill/find_if/rotate → std::fill/find_if/rotate
15. `splash/SplashXPathScanner.cc` - std::ranges::sort → std::sort
16. `utils/pdfsig.cc` - std::ranges::find → std::find
17. `utils/printencodings.cc` - std::ranges::sort → std::sort

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| freetype2 | 26.1.20 | 预装 |
| fontconfig | 2.16.0 | 预装 |
| zlib | 1.3.1 | 预装 |
| libopenjp2 | 2.5.2 | 预装 |
| libjpeg | 2.1.5.1 | 预装 |
| lcms2 | 2.19 | 预装 |
| libcurl | 8.19.0 | 预装 |
| libtiff | 4.7.1 | 预装 |
| libpng | 1.6.39 | 预装 |
| libiconv | 1.17 | 预编译包安装 |

## 验证结果

### 编译验证
```bash
# 编译完成度
ls ~/tmp/test-install-poppler-25.11.0/storage/Users/currentUser/usr/local/bin/
# 输出: pdfattach, pdfdetach, pdffonts, pdfimages, pdfinfo, pdfseparate, pdftohtml, pdftoppm, pdftops, pdftotext, pdfunite

ls ~/tmp/test-install-poppler-25.11.0/storage/Users/currentUser/usr/local/lib/
# 输出: libpoppler.so, libpoppler-cpp.so
```

### 功能验证（跳过）
poppler 测试数据不可用，跳过 make test。

## 注意事项

1. **C++20 兼容性**: poppler 25.11.0 大量使用 C++20 std::ranges，Clang 15 支持有限，需要17个补丁
2. **Iconv 配置**: cmake 的 FindIconv 需要 .pc 文件或显式路径
3. **libiconv 符号链接**: 预编译包安装后需要手动创建 libiconv.so 符号链接
4. **C 数组**: std::ranges 对容器支持，对 C 数组需要特殊处理

---
**编译结束**: 2026-05-26 17:40
**最终状态**: built（编译成功，需要进一步验证）