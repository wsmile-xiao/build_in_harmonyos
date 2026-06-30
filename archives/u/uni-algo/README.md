# uni-algo

Unicode 算法库 — C++17 header-only 友好的 Unicode 处理库。

## 简介

uni-algo 是一个轻量级 C++ Unicode 算法库，提供 UTF-8/UTF-16/UTF-32 转换、大小写转换、Unicode 规范化、文本分段、码点属性查询等功能。支持 Unicode 15.1.0 标准。

## 已编译版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.2.0 | published | CMake | 2026-06-18 |

## 依赖

无外部库依赖。仅需 C++17 兼容编译器。

## 构建方式

```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..
make -j2
make install
```

## 产物

- 静态库：`lib/libuni-algo.a`
- 头文件：`include/uni_algo/`（53 个 .h 文件）
- CMake 集成：`share/uni-algo/cmake/`（支持 `find_package(uni-algo)`）

## 测试

```bash
cd test
mkdir build_test && cd build_test
cmake .. -DBUILD_UNI_ALGO=ON
make -j2
ctest --output-on-failure
```

所有测试通过（17 个子测试项，2 项因未下载 Unicode 测试文件而跳过）。
