# libcuckoo-acp

## 简介

libcuckoo-acp 是高性能并发哈希表库 libcuckoo（上游 v0.3.1）的 HarmonyOS PC 适配包。
基于 Cuckoo 哈希算法，支持无锁查找和细粒度锁写入；纯头文件库（`libcuckoo/*.hh` +
`libcuckoo-c` 模板源），消费方仅需 C++11 及以上编译器。

## OHOS 适配

- Header-only 库：CMake 构建仅安装头文件与 CMake 配置文件，不产生二进制库。
- 上游测试开关 `BUILD_TESTS=ON` 在配方 `generate()` 中开启，`build()` 内以
  `ctest --output-on-failure` 完整执行 10 个 ctest 注册项（单测 1 + 压力 2 +
  通用基准 7），计数以 ctest 输出逐行解析为准。
- CMake 4.x 兼容性修复沿用历史归档结论：`build()` 内运行时改写上游
  `cmake_minimum_required(VERSION 3.1.0)` 为 `3.5.0...3.31`，不带补丁文件。
- 线程支持来自系统 libc（musl），`package_info()` 保留 `system_libs=["pthread"]`。

## 依赖

- 无 Conan 依赖（`find_package(Threads)` 由系统工具链提供）。
- 消费方需要 C++11 或更高标准。

## 功能验证

```cpp
#include <libcuckoo/cuckoohash_map.hh>
// test_package/test_libcuckoo_acp.cpp：insert/find/erase/update/upsert/
// locked_table/clear/empty/异常 find 共 10 项真实 API 检查
```

## 参考

- 上游主页: https://github.com/efficient/libcuckoo
- 上游版本: https://github.com/efficient/libcuckoo/archive/refs/tags/v0.3.1.tar.gz
- 历史归档: archives/l/libcuckoo/0.3.1/（同上游版本的早期适配结论）
