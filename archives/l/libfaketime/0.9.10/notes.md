# libfaketime 0.9.10 编译笔记

## 编译日期
2026-05-22

## 编译状态
**success** - 编译成功，功能验证通过

## 源码信息
- 版本: 0.9.10
- 来源: GitHub (wolfcw/libfaketime)
- URL: https://github.com/wolfcw/libfaketime/archive/refs/tags/v0.9.10.tar.gz

## 遇到的问题与解决方案

### 问题 1: SSL 证书验证失败
- **现象**: Savannah 官方下载源 SSL 证书验证失败
- **解决方案**: 从 GitHub 仓库下载源码

### 问题 2: 不支持的编译器警告选项
- **现象**: `-Wno-nonnull-compare` 在 Clang 15.0.4 中不被识别
- **错误**: `error: unknown warning option '-Wno-nonnull-compare' [-Werror,-Wunknown-warning-option]`
- **解决方案**: 移除该编译选项（补丁 0001-makefile-ohos-adapt.patch）

### 问题 3: GLIBC 符号版本不支持
- **现象**: 链接时出现 `undefined version GLIBC_2.2` 等错误
- **原因**: 鸿蒙系统使用 musl libc，不支持 glibc 的符号版本机制
- **涉及的符号**:
  - `timer_gettime@GLIBC_2.2`, `timer_gettime@@GLIBC_2.3.3`
  - `timer_settime@GLIBC_2.2`, `timer_settime@@GLIBC_2.3.3`
  - `pthread_cond_timedwait@GLIBC_2.2.5`
  - `pthread_cond_init@@`, `pthread_cond_destroy@@`
- **解决方案**:
  1. 注释掉版本脚本链接选项（Makefile）
  2. 注释掉源码中的 `__asm__(".symver ...")` 指令（libfaketime.c）
  - 补丁: 0002-disable-glibc-symver.patch

## 编译环境
- 编译器: Clang 15.0.4
- 目标平台: aarch64-unknown-linux-ohos
- C 库: musl libc
- PREFIX: ~/usr/local

## 编译产物
- `bin/faketime` - 命令行包装器 (30KB)
- `lib/faketime/libfaketime.so.1` - 单线程版本库 (90KB)
- `lib/faketime/libfaketimeMT.so.1` - 多线程版本库 (94KB)
- `share/man/man1/faketime.1.gz` - 手册页

## 功能验证
- 版本检查: `faketime --version` 输出 "Version 0.9.10" ✓
- 基本功能: `faketime '2020-01-01 00:00:00' date` 成功模拟时间 ✓

## 知识提取
- **平台适配**: musl libc 不支持 GLIBC 符号版本机制，需要禁用 `__asm__(".symver ...")` 指令
- **编译器差异**: Clang 可能不支持某些 GCC 特有的警告选项

---
**编译结束**: 2026-05-22 11:34
**最终状态**: success (published)