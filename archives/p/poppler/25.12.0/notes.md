# poppler 25.12.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 解压源码
tar xf poppler-25.12.0.tar.xz
cd poppler-25.12.0

# 2. 创建构建目录
mkdir build && cd build

# 3. CMake 配置
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DENABLE_BOOST=OFF \
  -DENABLE_CPP=ON \
  -DENABLE_GLIB=OFF \
  -DENABLE_GOBJECT_INTROSPECTION=OFF \
  -DENABLE_GTK_DOC=OFF \
  -DENABLE_QT5=OFF \
  -DENABLE_QT6=OFF \
  -DENABLE_UNSTABLE_API_ABI_HEADERS=ON

# 4. 编译
make -j2

# 5. 安装到 staging 目录
make install DESTDIR=$HOME/tmp/test-install-poppler-25.12.0

# 6. 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++23 std::ranges 兼容性错误 | clang++ 启用 C++23 后，std::ranges 算法与 poppler 代码冲突 | 为所有 std::ranges 算法添加 `std::` 前缀限定（37 个文件） |
| 2 | 字体宽度表编译失败 | 预生成的字体宽度表使用了 `std::ranges::copy` | 改用 `std::copy` 或添加 `std::` 限定 |
| 3 | PDF 文档处理相关错误 | 文档处理代码使用了未限定的 ranges 算法 | 统一修复所有 `ranges::` 调用 |

## 源码修改

### C++23 std::ranges 兼容性修复

修复了 37 个源文件中的 std::ranges 兼容性问题：

**核心修改模式**：
```cpp
// 修改前（C++23 冲突）
using std::ranges::copy;
copy(src.begin(), src.end(), dst.begin());

// 修改后（兼容）
std::copy(src.begin(), src.end(), dst.begin());
```

**涉及文件**：
- CMakeLists.txt (1)
- cpp/ 目录 (3 个文件)
- fofi/ 目录 (1 个文件)
- poppler/ 目录 (27 个文件，含字体宽度表)
- qt5/tests/ 和 qt6/tests/ (4 个文件，已禁用但修复)
- splash/ 目录 (3 个文件)
- utils/ 目录 (2 个文件)

**补丁列表**：
- 0001-CMakeLists.txt.patch
- 0002-cpp-poppler-document.cpp.patch
- 0003-cpp-poppler-image.cpp.patch
- 0004-fofi-FoFiTrueType.cc.patch
- 0005-poppler-Annot.cc.patch
- 0006-poppler-CIDFontsWidthsBuilder.h.patch
- 0007-poppler-Catalog.cc.patch
- 0008-0028-poppler-*Widths.pregenerated.c.patch (21 个字体宽度表)
- 0029-0032-qt*-tests-*.patch (4 个测试文件)
- 0033-0035-splash-*.patch (3 个文件)
- 0036-0037-utils-*.patch (2 个文件)

## 依赖版本

- cmake: 3.28.3
- clang: 18.1.8
- fontconfig: 2.15.0 (系统预装)
- freetype: 2.13.2 (系统预装)

## 验证结果

```bash
# 库文件验证
$ ls -lh ~/usr/local/lib/libpoppler*
-rwxr-xr-x 1 test test 4.68M May 19 15:10 /storage/Users/currentUser/usr/local/lib/libpoppler.so
-rwxr-xr-x 1 test test 133K May 19 15:10 /storage/Users/currentUser/usr/local/lib/libpoppler-cpp.so

# 可执行文件验证
$ ls ~/usr/local/bin/pdf*
pdfattach    pdfdetach    pdffonts     pdfimages    pdfinfo      pdfseparate  pdftohtml    pdftoppm     pdftops      pdftotext    pdfunite

# 功能验证
$ pdfinfo --version
pdfinfo version 25.12.0
Copyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org

$ pdftotext --version
pdftotext version 25.12.0
Copyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpoppler.so | 4.68 MB | 核心库 |
| libpoppler-cpp.so | 133 KB | C++ 封装库 |
| pdfattach | 15 KB | PDF 附件工具 |
| pdfdetach | 15 KB | PDF 分离附件工具 |
| pdffonts | 15 KB | PDF 字体分析工具 |
| pdfimages | 19 KB | PDF 图像提取工具 |
| pdfinfo | 15 KB | PDF 信息工具 |
| pdfseparate | 15 KB | PDF 页面分离工具 |
| pdftohtml | 87 KB | PDF 转 HTML 工具 |
| pdftoppm | 23 KB | PDF 转 PPM 工具 |
| pdftops | 19 KB | PDF 转 PS 工具 |
| pdftotext | 19 KB | PDF 转文本工具 |
| pdfunite | 15 KB | PDF 合并工具 |

## 注意事项

1. **C++23 兼容性**：所有补丁都针对 C++23 std::ranges 兼容性问题，补丁类型为 `platform_only`，需要添加 `#ifdef __OHOS__` 守卫
2. **字体宽度表**：21 个预生成的字体宽度表文件都进行了相同的修复
3. **Qt 绑定**：本次编译禁用了 Qt5/Qt6 绑定，但补丁已覆盖相关文件以备后续启用
4. **依赖管理**：编译时禁用了 boost 和 glib 依赖，仅保留核心功能

---
**编译结束**: 2026-05-19 15:15
**最终状态**: built
---

**编译结束**: 2026-05-19 15:19
**最终状态**: built
