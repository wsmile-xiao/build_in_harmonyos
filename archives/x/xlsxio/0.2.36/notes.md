# xlsxio 0.2.36 编译笔记

## 基本信息
- 软件: xlsxio 0.2.36
- 构建系统: CMake
- 编译器: clang 15.0.4
- 编译模式: 静态库

## 依赖
- zlib 1.3.1 (预安装)
- minizip 1.3.1 (从 zlib contrib 源码编译)
- expat 2.7.1 (从源码编译)

## 编译参数
```bash
cmake .. \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_C_FLAGS="-fPIC -O2" \
  -DBUILD_STATIC=ON \
  -DBUILD_SHARED=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TOOLS=ON \
  -DBUILD_PC_FILES=ON \
  -DMINIZIP_DIR=$DEFAULT_PREFIX \
  -DEXPAT_DIR=$DEFAULT_PREFIX \
  -DZLIB_DIR=$DEFAULT_PREFIX
```

## 注意事项
1. CMakeLists.txt 中 CMAKE_MINIMUM_REQUIRED(VERSION 2.6) 与 CMake 4.x 不兼容，需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
2. minizip 头文件需要安装在 include/minizip/ 子目录下，因为 xlsxio 使用 `#include <minizip/unzip.h>`
3. cmake 生成的 .pc 文件中库名为 libxlsxio_read/libxlsxio_write

## 功能测试
- CSV → XLSX → CSV 往返测试通过
- xlsxio_xlsx2csv 和 xlsxio_csv2xlsx 命令行工具正常工作

**编译开始**: 2026-06-24
**最终状态**: 成功
---

**编译结束**: 2026-06-24 11:31
**最终状态**: published
