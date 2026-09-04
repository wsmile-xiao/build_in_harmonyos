# value-ptr-lite

A C++ smart-pointer with value semantics for C++98, C++11 and later — single-file header-only library.

## 简介

value-ptr-lite 是 nonstd-lite 家族的单文件 header-only C++ 库，
提供具有值语义的智能指针 `nonstd::value_ptr`（C++98 及更高版本）。

## OHOS 适配

- 官方 tag v0.2.1 源码，header-only，无编译产物。
- Conan 配方按 Conan 2.x 重写（package_type=header-library + CMakeToolchain）。
- 上游 lest 测试 cpp98/11/14/17 四变体 51/51 全过。
- test_package 消费者测试真实调用 value_ptr API（R34）。

## 依赖

无（header-only，零编译依赖）。

## 参考

- 上游: https://github.com/nonstd-lite/value-ptr-lite
- 版本: 0.2.1
