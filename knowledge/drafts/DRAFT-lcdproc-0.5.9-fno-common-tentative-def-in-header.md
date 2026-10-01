# DRAFT-lcdproc-0.5.9-fno-common-tentative-def-in-header：`-fno-common` 重复符号——头文件里的 tentative definition

> Status: Draft | Updated: 2026-09-29
> Source: lcdproc 0.5.9 适配（`feat/lcdproc-0.5.9`）补丁 `0003-iface-extern-definition.patch`
> 对应：`knowledge/drafts/DRAFT-lcdproc-0.5.9-fno-common-tentative-def-in-header.kv`

## 现象

2014 年代的 C 工程，源码是干净的、头文件也没写错，但用 clang 链接时报：

```console
ld.lld-15: error: duplicate symbol: iface
>>> defined at main.c
>>> main.o:(iface)
>>> defined at iface.c
>>> iface.o:(.bss+0x0)
```

**同一份代码在宿主 gcc 上照编不误。**

## 根因

`clients/lcdproc/iface.h` 在**头文件**里放了一个 tentative definition：

```c
/** max number of interfaces in multi-interface mode */
#define MAX_INTERFACES 3

IfaceInfo iface[MAX_INTERFACES];   /* interface info */
```

这个文件被 `clients/lcdproc/main.c` 和 `clients/lcdproc/iface.c` 同时 `#include`。

- **C89/C90 语义**：头文件里无 initializer 的对象声明是"一个定义"，
  不是"一个声明"。所以每个 include 它的 TU 都会生成一份。
- **GCC 老版本**（默认 `-fcommon`）：把跨 TU 的这些定义合并成一个
  `COMMON` 符号——同 size 同 type 时**静默合并**，于是能编过。
- **clang ≥ 11**（默认 `-fno-common`，跟随上游 GCC 10+）：每个 TU 各自
  生成一个**强 `.bss` 定义**，链接期撞车。

所以这不是"某个 TU 多写了一遍"，而是"同一份头文件被 N 个 TU 展开成 N 个定义，
而 N 恰好等于 1 的时候没人发现"。

### 两个容易踩的坑

1. **报错文本里的 `defined at main.c` 是误导**。它指的是 `main.c` 展开
   `#include "iface.h"` 后的那一行，不是 `main.c` 自己写的。定位要去**头文件**里找。
2. **"宿主 gcc 能编过"不等于代码没问题**。宿主 gcc 版本旧 + 用 bfd + 默认
   `-fcommon`，这类缺陷可以潜伏十几年。必须用**目标工具链**
   （clang 15 + ld.lld）编一遍才算验证过。HarmonyOS PC 的 NDK 恰恰就是
   clang + lld，所以这个缺陷在 OHOS 上是**默认命中**而不是偶发。

## 正解

拆成"头文件 `extern` 声明 + 一个 `.c` 里的唯一定义"——C89 之后的标准写法：

```diff
--- a/clients/lcdproc/iface.h
+++ b/clients/lcdproc/iface.h
@@ -18,7 +18,7 @@
 /** max number of interfaces in multi-interface mode */
 #define MAX_INTERFACES 3

-IfaceInfo iface[MAX_INTERFACES];	/* interface info */
+extern IfaceInfo iface[MAX_INTERFACES];	/* interface info */

 /** Update screen content */
 int iface_screen(int rep, int display, int *flags_ptr);
--- a/clients/lcdproc/iface.c
+++ b/clients/lcdproc/iface.c
@@ -29,6 +29,10 @@
 #include "util.h"
 #include "iface.h"

+/** Shared network-interface table, defined here and declared (extern)
+ * in iface.h so every including translation unit links to this one copy. */
+IfaceInfo iface[MAX_INTERFACES];
+
 #define UNSET_INT -1
 #define UNSET_STR "\01"
```

## 定位方法：先确认"是不是全树唯一"

改之前先扫一遍全树，**别只修报错的那一处**：

```sh
# 头文件里无 extern、无 initializer 的数组/结构体定义
grep -rnE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_[:space:]*]*[[:space:]]+[A-Za-z_][A-Za-z0-9_]*\[[^]]*\][[:space:]]*;' \
    --include='*.h' . | grep -v extern
# 确认它被几个 TU include
grep -rl '#include "iface.h"' . | wc -l
```

lcdproc 0.5.9 扫出来**只有这一处**。两处看起来像的**不是**问题：

- `server/drivers/*.h` 里的 `MODULE_EXPORT char *api_version`
  —— 这是各驱动 `.so` 各自的**模块 ABI**，每个 `.so` 本就该有一份，不是冲突。
- `port.h` 里那个是 `static`（内部链接），天然不冲突。

这个区分很重要：不做这步就容易把"正常的模块 ABI"误改成 `extern`，
把一个正常的共享库接口改成链接期未定义符号。

## 为什么不选 `-fcommon`

加 `-fcommon` 能编过，但：

- **掩盖而非修复**——以后任何人再往头文件写 tentative definition 都不会暴露；
- 收益为零——本树只有这一处问题，改一行比加一个全局旗标更可控；
- 旗标会传染到所有 TU，且与目标工具链的默认行为相悖。

`static` 也是个选项（内部链接、各 TU 一份副本，天然不冲突），但**前提是该对象
不需要跨 TU 共享可变状态**。`iface[]` 是要跨 `main.c` / `iface.c` 共享的，
所以只能用 `extern` + 唯一定义。
