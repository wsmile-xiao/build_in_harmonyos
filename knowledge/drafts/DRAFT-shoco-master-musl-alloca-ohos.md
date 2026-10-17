# DRAFT-shoco-master-musl-alloca-ohos：OHOS/musl 下 alloca() 需显式包含 <alloca.h>

> Contributor: pc1-47 | Status: Draft | Updated: 2026-09-17
> Source: shoco master 适配（conan-verify G2 迭代链）

## 背景

shoco 是零依赖 C99 短字符串压缩库（纯 Makefile）。其 CLI（shoco-bin.c）在读取文件时用
`alloca()` 分配栈缓冲区。在 glibc Linux 环境下直接编译通过（glibc 的 `<stdlib.h>` 在
`__GNUC__` 下隐式声明 alloca），移植到 OHOS（musl 派生 libc）后编译产生：

```
shoco-bin.c:60:25: warning: call to undeclared function 'alloca'; ISO C99 and later do
  not support implicit function declarations [-Wimplicit-function-declaration]
shoco-bin.c:60:17: warning: cast to 'char *' from smaller integer type 'int' [-Wint-to-pointer-cast]
...
ld.lld: error: undefined symbol: alloca
```

根因：musl 的 `<stdlib.h>` 不提供 alloca 的隐式声明，`-std=c99` 下隐式声明本身被标为
警告，符号缺失直接落到链接期。这是 glibc → musl libc 边界差异，OHOS（musl 派生）必现。

## 修复

在调用 alloca 的源文件显式包含 `<alloca.h>`（glibc 与 musl 均提供该头文件，语义一致）：

```patch
--- a/shoco-bin.c
+++ b/shoco-bin.c
@@ -1,4 +1,5 @@
 #include <stdio.h>
+#include <alloca.h>
 #include <stdlib.h>
 #include <string.h>
```

验证：patch 应用后 `conan-verify shoco master` G2 PASS（编译 + 链接 + test_package 通过），
W3 本地 CI 通过。

## 适用范围与反例

- 适用：OHOS/其他 musl 系平台编译调用 alloca() 的上游 C/C++ 代码；典型为纯 Makefile 单文件
  C 工具（shoco-bin、endlessh 类）；上游 glibc 环境编译通过但未显式包含 <alloca.h> 的源码。
- 反例/不适用：已显式包含 <alloca.h> 的源码（无需改动）；MSVC 平台（无 alloca.h，用
  _alloca）；使用定长栈数组即可的用法（可改为栈数组，避免 alloca 依赖）。

## 查重差异

- 既有 E 条目均未覆盖该组合：E004（musl BIND_NOW 链接标志）、E115（fallocate 常量缺失 +
  __OHOS__ 守卫）、E063（-Werror 隐式声明）均不同根因；musl-glibc 对比文档 §1.10 仅记录
  alloca 可用性表，无错误模式与修复。
- 与 E063 同属"隐式声明"族（similar_to），但触发点（链接期 undefined symbol）与修复
  （补头文件而非禁 Werror）不同。
