# wcstools 3.9.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. `make all`（CFLAGS="-fPIC -O2 -D_FILE_OFFSET_BITS=64" CC=clang）
2. libwcs 由顶层 Makefile 递归构建为静态库

## 遇到的问题与解决方案
无阻塞问题。Clang 15 对 K&R C 产生大量 -Wdeprecated-non-prototype 警告。

## 验证结果
- conan create/verify: 通过 | finish + W3: 通过
- 运行时 smoke: 2/2 | artifact: 52/52

## 注意事项
上游无自动化测试入口（Makefile 无 check/test，无 test/ 目录）
---
---

**编译结束**: 2026-07-27 21:15
**最终状态**: built
