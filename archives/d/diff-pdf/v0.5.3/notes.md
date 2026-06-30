# diff-pdf v0.5.3 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile 替代原 autotools)
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build diff-pdf v0.5.3 --url=https://github.com/vslavik/diff-pdf/archive/refs/tags/v0.5.3.tar.gz` 初始化
2. 原 autotools 构建系统无法使用（缺 automake、wxWidgets、poppler-glib）
3. 创建自定义 Makefile 使用 poppler-cpp + cairo 替代 poppler-glib + wxWidgets
4. 重写 diff-pdf.cpp 移除 wxWidgets/poppler-glib 依赖，使用 poppler-cpp API
5. `make -j2` 编译成功
6. `make install DESTDIR=$TEST_PREFIX` staging 安装
7. `make install` 安装到 DEFAULT_PREFIX
8. `diff-pdf --help` 验证成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake 不可用 | precompiled automake 缺少 Perl 模块路径 | 安装 automake 预编译包，创建 perl 符号链接，创建 automake-1.17→1.16 symlink |
| 2 | wxWidgets 不可用 | OpenHarmony 平台无 wxWidgets | 移除 wxWidgets 依赖，使用 getopt 替代 wxCmdLineParser |
| 3 | poppler-glib 不可用 | poppler 编译时未启用 glib bindings | 使用 poppler-cpp C++ API 替代 poppler-glib |
| 4 | cairo-ft.h 不可用 | CairoOutputDev 需要 cairo-ft.h 但 Cairo 未编译 FreeType 支持 | 使用 poppler-cpp page_renderer (Splash) 替代 CairoOutputDev 渲染 |
| 5 | C++17 缺 std::optional | poppler 头文件需要 C++17 | 添加 -std=c++17 编译选项 |

## 源码修改

### 0001-Makefile.patch
- 新增自定义 Makefile，使用 poppler-cpp + cairo 链接
- 编译选项: CXX=clang++, CXXFLAGS=-fPIC -O2 -std=c++17

### 0002-diff-pdf.cpp.patch
- 移除 wxWidgets 所有依赖 (wxApp, wxCmdLineParser, wxFrame 等)
- 移除 poppler-glib 所有依赖 (PopplerDocument, PopplerPage 等)
- 使用 poppler-cpp C++ API (poppler::document, poppler::page, poppler::page_renderer)
- 使用 getopt_long 替代 wxCmdLineParser 命令行解析
- 使用自定义 Rect 替代 wxRect
- 保留核心 PDF 对比功能 (像素级比较、diff 输出、--output-diff PDF 生成)
- GUI (--view 模式) 已移除，仅支持 headless 命令行模式

## 依赖版本

- poppler/23.12.0 (poppler-cpp)
- cairo/system (cairo-pdf)
- zlib/system
- automake/1.16.5 (构建工具)

## 验证结果

```bash
$ diff-pdf --help
Usage: diff-pdf [OPTIONS] file1.pdf file2.pdf
Options:
  -h, --help                  Show this help message
  -v, --verbose               Be verbose
  -s, --skip-identical        Only output pages with differences
  -m, --mark-differences      Additionally mark differences on left side
  -g, --grayscale             Only differences in color, unchanged in gray
      --output-diff=FILE      Output differences to given PDF file
      --channel-tolerance=N   Channel values equal if within tolerance
      --per-page-pixel-tolerance=N  Pixels allowed to differ per page
      --dpi=N                 Rasterization resolution (default: 300 dpi)
```

## 注意事项

- 本编译为 headless 版本，移除了 wxWidgets GUI 依赖
- --view 模式不可用（需要 wxWidgets）
- 使用 poppler-cpp (Splash renderer) 替代 poppler-glib (Cairo renderer)，渲染质量可能略有差异
- poppler-cpp 不需要 glib2 绑定，降低了依赖复杂度
---

**编译结束**: 2026-05-25 22:16
**最终状态**: built
