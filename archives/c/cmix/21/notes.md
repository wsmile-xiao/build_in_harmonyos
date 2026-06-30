# cmix 21 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，非 autotools)
- 编译日期: 2026-06-25
- 编译器: clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. init-build 下载源码并初始化归档
2. 修改 makefile: `CC = clang++-17` → `CC = clang++`（系统仅有 clang++ 15.0.4）
3. 修改 src/models/fxcmv1.cpp: 用 `#if defined(__x86_64__) || defined(__i386__)` 守卫 `#include <immintrin.h>` 和 x86 SIMD typedefs
4. 执行 `make cmix -j1` 编译主二进制
5. 手动安装到 staging 目录（无 install 目标）：`cp cmix $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
6. 功能测试：压缩/解压往返测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#include <immintrin.h>` 编译失败 | immintrin.h 是 x86 专用头文件，aarch64 平台不支持 | 用 `#if defined(__x86_64__) \|\| defined(__i386__)` 守卫 include 和 SIMD typedefs，aarch64 走标量 #else 分支 |
| 2 | `CC = clang++-17` 找不到编译器 | makefile 硬编码了 clang++-17 版本，系统仅有 clang++ 15.0.4 | 修改 makefile 中 CC 为 clang++ |

## 源码修改

| 文件 | 修改内容 | 原因 |
|------|---------|------|
| makefile | `CC = clang++-17` → `CC = clang++` | 系统无 clang++-17，使用默认 clang++ |
| src/models/fxcmv1.cpp | 用 `#if defined(__x86_64__) \|\| defined(__i386__)` 守卫 `#include <immintrin.h>`、`typedef __m128i XMM`、`typedef __m256i YMM` | x86 SIMD 头文件在 aarch64 不可用，代码已有标量 #else 回退实现 |

## 依赖版本

- 无外部依赖（纯 C++ 项目）
- 编译器: clang++ 15.0.4
- make: GNU Make 4.4.1

## make check

- 无 make check / make test 目标
- 改为手动功能验证：压缩→解压往返测试

## 验证结果

### 版本信息
```
$ cmix
cmix version 21
Compress:
    with dictionary:    cmix -c [dictionary] [input] [output]
    without dictionary: cmix -c [input] [output]
    force text-mode:    cmix -t [dictionary] [input] [output]
    no preprocessing:   cmix -n [input] [output]
    only preprocessing: cmix -s [dictionary] [input] [output]
                        cmix -s [input] [output]
Decompress:
    with dictionary:    cmix -d [dictionary] [input] [output]
    without dictionary: cmix -d [input] [output]
```
退出码: 0

### ELF 格式验证
```
$ file /storage/Users/currentUser/usr/local/bin/cmix
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

### 压缩测试（393 字节英文文本）
```
$ cmix -n cmix-rt-test.txt cmix-rt-test.cmx
393 bytes -> 231 bytes in 66.01 s.
```
耗时: real 1m6.407s, user 1m2.026s, sys 0m4.089s
压缩率: 58.8% (393→231 字节)

### 解压测试
```
$ cmix -d cmix-rt-test.cmx cmix-rt-test-out.txt
231 bytes -> 393 bytes in 65.34 s.
```
耗时: real 1m5.734s, user 1m1.960s, sys 0m3.487s

### 往返一致性验证
```
$ diff cmix-rt-test.txt cmix-rt-test-out.txt
（无输出 = 文件完全一致）
```
结果: PASSED

### MD5 校验
```
原始文件 MD5: ed2d7ad05ac63d0b28ebc1f72c7cbbfc
解压文件 MD5: ed2d7ad05ac63d0b28ebc1f72c7cbbfc
```
结果: PASSED (MD5 完全一致)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cmix | 1788480 bytes | ELF 64-bit aarch64 动态链接可执行文件 |

## 注意事项

- cmix 使用大量内存（README 建议 32GB RAM 用于运行），编译时使用 -j1 避免内存不足
- 编译时未使用 -Ofast -march=native（仅 all 目标添加），cmix 目标使用基础 -std=c++14 -Wall
- 压缩/解压速度非常慢（68字节文件耗时约55秒），这是 cmix 的设计特点（追求最高压缩比）
- fxcmv1.cpp 中的 x86 AVX2/SSE SIMD 代码在 aarch64 上自动回退到标量实现，功能正确但性能较低
---

**编译结束**: 2026-06-25 12:37
**最终状态**: built
