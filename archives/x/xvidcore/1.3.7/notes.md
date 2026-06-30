# xvidcore 1.3.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. 下载源码: xvidcore-1.3.7.tar.gz
2. 解压后嵌套源码提升 (build/generic → 根目录)
3. 修复 config.guess / config.sub 以支持 HarmonyOS (aarch64-unknown-linux-ohos)
4. 修复 configure 中 umask 077 → umask 002 (HMDFS 权限兼容)
5. 修复 sources.inc 中 SRC_DIR (../../src → src)，从 tarball 解压 src 目录
6. ./configure --prefix=/storage/Users/currentUser/usr/local
7. make (单线程)
8. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2013 版本不支持 aarch64-ohos | 替换为 2024 版 config.guess/config.sub |
| 2 | configure 临时目录创建权限失败 | HMDFS umask 077 导致目录组权限为零 | 修改 configure 中 umask 077 → umask 002 |
| 3 | 源码目录找不到 (SRC_DIR=../../src) | 嵌套提升后 src 目录不在正确位置 | 从 tarball 解压 src 目录 + 修改 sources.inc 中 SRC_DIR |

## 源码修改

修改的文件:
- config.guess: 替换为 2024 版本 (支持 aarch64-unknown-linux-ohos)
- config.sub: 替换为 2024 版本 (支持 aarch64-unknown-linux-ohos)
- configure: umask 077 → umask 002 (HMDFS 权限兼容)
- sources.inc: SRC_DIR = ../../src → SRC_DIR = src

## 依赖版本

- clang 15.0.4
- llvm-ar, llvm-ranlib (LLVM)
- GNU Make 4.4.1
- autoconf 2.72

## 验证结果

```bash
# 无 make check 目标，xvidcore 不提供测试套件
# 二进制验证:
file libxvidcore.so.4.3 → ELF 64-bit LSB shared object, ARM aarch64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libxvidcore.a | 684782 字节 | 静态库 |
| libxvidcore.so.4.3 | 555392 字节 | 动态共享库 |
| xvid.h | 34417 字节 | 头文件 |

## 注意事项

- xvidcore 源码树嵌套结构 (build/generic + src/) 在 ohc 提升后需要手动处理 src 目录
- HMDFS 文件系统 umask 行为特殊，077 会剥夺组权限导致临时目录不可写
- 无官方测试套件 (make check 不存在)
---

**编译结束**: 2026-06-02 10:53
**最终状态**: built
