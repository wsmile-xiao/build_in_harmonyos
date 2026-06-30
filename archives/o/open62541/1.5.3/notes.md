# open62541 1.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码并解压到 ~/tmp/builds/open62541-1.5.3.work
2. 创建 out-of-source 构建目录: mkdir build && cd build
3. cmake 配置: cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ $BUILD_SRC_DIR
4. make -j1 编译
5. make install DESTDIR=$TEST_PREFIX (staging 验证)
6. verify-build PASS (G2 有 1 个 warning: 无二进制可执行文件 — open62541 是纯库包)
7. ohc-run.py package 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bits/stdio_lim.h 不存在 | glibc 特有头文件，musl/OHOS 无此文件 | 在 eventloop_posix.h 中添加 `#ifndef __OHOS__` 守卫 |
| 2 | sockaddr_storage 重定义 | linux/net_tstamp.h 与 sys/socket.h 冲突 | 在 eventloop_posix_eth.c 中添加 `#ifndef __OHOS__` 守卫跳过 linux/net_tstamp.h |
| 3 | struct sock_txtime / SOF_TXTIME_REPORT_ERRORS 未定义 | 因跳过 linux/net_tstamp.h 导致 | 将 `#ifndef SO_TXTIME` 改为 `#if !defined(SO_TXTIME) || defined(__OHOS__)` 守卫 txtime 功能 |

## 源码修改

1. arch/posix/eventloop_posix.h — 添加 `#ifndef __OHOS__` 守卫 `#include <bits/stdio_lim.h>` (R8)
2. arch/posix/eventloop_posix_eth.c — 添加 `#ifndef __OHOS__` 守卫 `#include <linux/net_tstamp.h>` (R8)
3. arch/posix/eventloop_posix_eth.c — 修改 `#ifndef SO_TXTIME` → `#if !defined(SO_TXTIME) || defined(__OHOS__)` 守卫 txtime 功能块 (R8)
4. arch/posix/eventloop_posix_eth.c — 修改 `#ifdef SO_TXTIME` → `#if defined(SO_TXTIME) && !defined(__OHOS__)` 守卫 send_txtime 函数定义和调用 (R8)

## 验证结果

ctest: 无测试 (cmake 默认不启用单元测试，需 -DUA_BUILD_UNIT_TESTS=ON)
verify-build: PASS (G1 PASS, G2 PASS⚠️1, G3 PASS, G4 PASS)
质量报告: 无二进制可执行文件(warning, 纯库包预期行为)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| open62541-1.5.3-ohos-aarch64.tar.gz | 9115KB | 预编译包 |
| libopen62541.a | ~3MB | OPC UA 静态库 |

## 注意事项

- open62541 是纯库包(无可执行文件)，G2 的"无二进制文件" warning 为预期行为
- 需 4 处 OHOS 平台适配补丁，均为 `#ifdef __OHOS__` 守卫(R8)
- ctest 无测试用例，需启用 -DUA_BUILD_UNIT_TESTS=ON 才有测试
---

**编译结束**: 2026-06-15 11:29
**最终状态**: built
