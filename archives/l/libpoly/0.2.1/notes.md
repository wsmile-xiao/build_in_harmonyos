# libpoly 0.2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤
改用 gmp/6.3.0.1（gmpxx.h）编 poly+polyxx，`BUILD_TESTING=ON` 真机 ctest 15/15（200 TEST_CASE 全过）。u_memstream 不用 open_memstream，改 mkstemp。`CREATE_EXIT:0`；`libpoly version=0.2.1 6+7=13 ok`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | polyxx 缺 gmpxx.h | gmp/6.3.0 无 C++ 头 | 只 build target poly |
| 2 | -Werror | 上游默认 | 去掉 |

## 依赖版本
- gmp/6.3.0
