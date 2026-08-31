# libwapcaplet 0.4.3.1 适配笔记

## 编译环境
- 构建系统: custom（NetSurf Makefile → standalone Makefile 替换）
- 编译日期: 2026-06-06
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载源码包 `libwapcaplet-0.4.3-src.tar.gz` 并解压
2. 发现原始 Makefile 依赖 NetSurf 构建系统 (`netsurf-buildsystem`)，不可用于此平台
3. 创建独立 Makefile 替换 NetSurf 构建系统，保留所有编译标志（去除 -Werror 以兼容 clang）
4. 编译: `make PREFIX=$DEFAULT_PREFIX`
5. 安装: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. 创建自定义测试程序验证库功能（原测试套件依赖 libcheck 不可用）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NetSurf 构建系统依赖 (`NSSHARED`) | 原始 Makefile include `$(NSSHARED)/makefiles/Makefile.tools`，NetSurf 构建系统不可用 | 创建独立 Makefile，手动定义所有编译和安装规则 |
| 2 | lld 链接器报错 (libxml2.so.16 缺失) | OHOS SDK 的 lld 需要 libxml2 但环境不满足 | 测试程序使用 GNU ld (`-fuse-ld=/data/service/hnp/bin/ld`)；库本身是 .a 静态库无需链接 |
| 3 | "check" 测试库不可用 | NetSurf 测试套件依赖 libcheck | 创建自定义 standalone 测试程序 (test_lwc.c)，覆盖核心功能验证 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile | NetSurf 构建系统不可用 | 完全替换为独立 Makefile | 待 refresh-patch 生成 |

## 依赖版本

- 无运行时依赖
- 编译工具: clang 15.0.4, llvm-ar, llvm-ranlib, GNU make 4.4.1, GNU sed

## 验证结果

```bash
$ ./test_lwc
PASS: Created string 'hello' (len=5, data='hello')
PASS: Interning same string returns same pointer (str1==str2)
PASS: Interning different string returns different pointer (str1!=str3)
PASS: lwc_string_isequal(str1,str2) = true
PASS: lwc_string_isequal(str1,str3) = false
PASS: lwc_string_caseless_isequal('hello','HELLO') = true
PASS: lwc_string_hash_value('hello') = 3069866343
PASS: lwc_intern_substring('hello',1,3) = 'ell' (len=3)

=== All tests passed ===
```

## 交付物

| 文件 | 说明 |
|------|------|
| libwapcaplet.a | 静态库 (6562 bytes, ELF64 aarch64) |
| libwapcaplet.pc | pkg-config 文件 (version 0.4.3.1) |
| libwapcaplet/libwapcaplet.h | 头文件 |

## 注意事项

- libwapcaplet 是 NetSurf 浏览器组件库，使用 NetSurf 自有的构建系统而非标准 autotools
- 此平台需替换为独立 Makefile 进行编译
- 静态库无需 ELF 签名（.a 文件不可直接执行）
- 测试需使用 GNU ld 替代 OHOS SDK 的 lld（lld 有 libxml2 依赖问题）
---

**编译结束**: 2026-08-27 00:26
**最终状态**: built
