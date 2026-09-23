# opendht 3.7.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤
开启 HTTP/proxy/peer-discovery。`BUILD_TESTING=ON` + cppunit/1.15.1 真机 ctest 10/10。`CREATE_EXIT:0`；`opendht version=3.7.1 hash=... ok`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-lmsgpack-cxx` | header-only | 只加 include，不链 .so |
| 2 | pkg-config 找 libargon2 | 制品仓名为 argon2 | 同时搜 argon2 |
| 3 | test 找不到 libgnutls.so.30 | gnutls 标成 static | test 显式拼 LD_LIBRARY_PATH |

## 依赖版本
- gnutls/3.8.10
- nettle/3.10.2.1
- argon2/20190702
- fmt/12.2.0
- msgpack-cxx/7.0.0
