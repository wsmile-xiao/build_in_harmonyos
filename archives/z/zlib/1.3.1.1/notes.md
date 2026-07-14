# zlib 1.3.1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built

## 编译步骤

CFLAGS="-fPIC -O2" ./configure --static --prefix=/  →  make -j1  →  make check

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 非-PIC libz.a 链进共享库(libcairo.so)报 R_AARCH64 relocation z_errmsg | 已发布 zlib/1.3.1 configure 未加 -fPIC | 适配修复：递增版本号至 1.3.1.1，CFLAGS=-fPIC 编，静态 libz.a 对象即 PIC |

## 源码修改

无补丁（源码为 zlib 1.3.1，仅构建旗标 CFLAGS=-fPIC）。

## 依赖版本

- 无 conan 依赖（仅系统库）

## 验证结果

- 真机 conan create + test_package 通过（fPIC libz.a 被 libcairo.so 吸收，全链 cairo ALL_PASS）

## 消费者（须用本版而非 1.3.1）
所有把 zlib 静态链进**共享库**的下游都必须 require `zlib/1.3.1.1`（-fPIC），不能用 `zlib/1.3.1`（非 -fPIC，
链进 .so 报 R_AARCH64 relocation）：cairo、libpng、**qpdf**、后续 **libtiff** 等。本版首发到制品仓即为解此依赖。
