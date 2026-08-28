# ataqv 1.3.1 适配笔记

## 编译环境
- 构建系统: Makefile（非 CMake/autotools）
- 编译日期: 2026-08-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/ParkerLab/ataqv/archive/refs/tags/1.3.1.tar.gz`
2. 安装 Conan 依赖: htslib/1.24-r0, boost/1.91.0.1.1, ncurses/6.6
3. 编译 boost iostreams 源码（zlib.cpp, gzip.cpp）以获得 zlib 支持
4. 创建 ncurses 符号链接（libncurses.a → libncursesw.a）
5. 生成 Version.hpp（`#define VERSION "1.3.1"`）
6. 编译 7 个源文件: ataqv.cpp, Features.cpp, HTS.cpp, IO.cpp, Metrics.cpp, Peaks.cpp, Utils.cpp
7. 链接: 静态 boost_iostreams.a + 共享 boost_filesystem/chrono + 静态 htslib + zlib/ncurses/lzma/libdeflate

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | boost_iostreams.so 无 zlib 符号 | Conan boost 包构建时未包含 zlib 依赖 | 从 boost 源码下载 iostreams 的 zlib.cpp/gzip.cpp，本地编译为静态库 |
| 2 | 链接找不到 -lboost_system | Boost 1.91 中 system 为 header-only | 移除 -lboost_system 链接标志 |
| 3 | 链接找不到 -llzma -ldeflate | htslib 静态库依赖 xz/libdeflate（传递依赖） | 显式添加 -llzma -ldeflate 到链接标志 |
| 4 | Makefile 用 -lncurses 但 conan 提供 libncursesw.a | conan ncurses 包用 wide 版本 | 创建 libncurses.a → libncursesw.a 符号链接 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| htslib | 1.24-r0 | Conan ohpcd |
| boost | 1.91.0.1.1 | Conan ohpcd |
| ncurses | 6.6 | Conan ohpcd |
| zlib | 1.3.1 | Conan ohpcd (via htslib) |
| xz | 5.6.2 | Conan ohpcd (via htslib) |
| libdeflate | 1.25 | Conan ohpcd (via htslib) |

## 验证结果

```bash
$ ./build/ataqv --version
1.3.1

$ ./build/ataqv --help
ataqv 1.3.1: QC metrics for ATAC-seq data
Usage: ataqv [options] organism alignment-file
...
```

## 注意事项

- Conan boost 包的 iostreams 库缺少 zlib 支持，conanfile.py 中包含 boost iostreams 源码文件（sources/boost_iostreams/）并在 build() 中单独编译
- ataqv 使用 Makefile 而非 CMake/autotools，conanfile.py 直接调用编译器命令
---

**编译结束**: 2026-08-27 15:50
**最终状态**: built
