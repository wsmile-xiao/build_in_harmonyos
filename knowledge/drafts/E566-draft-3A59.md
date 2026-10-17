# E566 — 纯 Makefile 项目头文件 typedef `__off64_t`：OHOS musl 缺该 glibc 私有类型，直接替换为标准 `off_t`

> Contributor: 3A59 | Status: Draft | Updated: 2026-09-21
> Source: fastahack 1.0.0 适配（HarmonyOS PC）
> 对应：`knowledge/drafts/E566-draft-3A59.kv`

## 现象

纯 Makefile（无 configure）项目在头文件里用 glibc 私有类型声明大文件偏移，OHOS（musl libc）编译直接报类型不存在：

```console
In file included from Fasta.cpp:9:
In file included from ./Fasta.h:19:
./LargeFileSupport.h:15:9: error: unknown type name '__off64_t'
typedef __off64_t off_type;
        ^
1 error generated.
```

## 触发条件

- 构建系统: 纯 make（Makefile），无 configure 脚本
- 阶段: make 编译（.cpp/.c 首文件编译即失败）
- 前提: 源码头文件（如 `LargeFileSupport.h`）在非 WIN32/Apple/FreeBSD 分支直接
  `typedef __off64_t off_type;` 实现大文件（LFS）支持

## 根因分析

`__off64_t` 是 glibc 私有 typedef（`#include <bits/types.h>` 内部），OHOS 的
musl libc 不提供。老代码为在 Linux 上启用大文件支持（`_FILE_OFFSET_BITS=64`）
直接引用 glibc 内部类型，导致 musl 平台编译失败。

## 解决方案

### 推荐方案

头文件已 `#define _FILE_OFFSET_BITS 64` 时，直接把 typedef 替换为标准 `off_t`：
`off_t` 在 LFS 宏下同为 64 位，语义完全等价，且是 POSIX 标准类型，musl/glibc
都提供。**纯 typedef 场景一行替换即可，无需平台宏双分支**（与 autotools 下用
libc 能力 guard `#if defined(__GLIBC__)` 的方案互补——本场景是头文件顶层无条件
分支，加宏分支反而侵入更多代码）。

```diff
 #else
 #define ftell64(a)     ftello(a)
 #define fseek64(a,b,c) fseeko(a,b,c)
-typedef __off64_t off_type;
+typedef off_t off_type;
 #endif
```

### 验证

替换后除编译通过外，应实测 LFS 64 位偏移真正生效（防止只是“编译过、功能坏”）：
构造 3×~1GB（总 >2GB）FASTA，索引后从偏移 >2GB 的序列提取子序列，确认
fseeko/ftello 在大偏移下工作（fastahack 实测：seq3 偏移 2,000,070,160 提取成功）。

```bash
make CXX=clang++ CXXFLAGS="-O3 -fPIC -D_FILE_OFFSET_BITS=64" -j1
# 构造 ~3GB fasta → fastahack -i → fastahack -r seq3:985950000..985950070
```

### 禁止做法

- ❌ 用 `#ifdef __OHOS__` 平台宏包住 glibc 分支（R8：patches 默认禁止平台宏；且 off_t 是通用 POSIX 修复，无需平台特判）
- ❌ 空壳 stub / return 0 掩盖偏移计算

## 关联条目

- 相关: [E414]（musl fpos_t 结构体误用，同族不同形态：E414 是 fpos_t 被当整数，
  本条目是 __off64_t typedef 缺失）
- 部分覆盖: [DRAFT-ohos-musl-glibc-isms-static-cxx-dep-linking]（cdo 2.6.3，
  autotools/libf2c 场景的 libc 能力双分支方案）