# DRAFT: musl/OHOS 缺 BSD 血统 `strlcat`/`strlcpy` 的补桥模式

> 草稿编号：DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge（待审核 promote）
> 来源：dasm 2.20.15-202011092.20.14.1 适配，2026-09-10
> 路径 B（知识库扩展）素材

## 问题

`strlcat`/`strlcpy` 源自 OpenBSD，**不是 C 标准库函数**：

| libc | 是否提供 |
|---|---|
| OpenBSD / FreeBSD / macOS | 原生提供 |
| glibc | **2.38（2023-08）起**才有 |
| **OHOS musl** | **没有** |

因此 2018–2020 年代在 macOS 上开发的 C 代码普遍"默认 libc 一定有"而直接调用：
在 glibc ≥2.38 的 Debian 上编得过，换到 OHOS musl 立刻失败。

失败形态随方言变化，容易误判：

```console
# 严格 ISO C（-std=c99/-std=c11，未定义 _POSIX_C_SOURCE）
$ clang -std=c99 -c t.c
t.c:2:42: error: call to undeclared function 'strlcat'; ISO C99 and later
          do not support implicit function declarations

# gnu 方言 / 老 clang
warning: implicit declaration of function 'strlcat'
$ clang ... -o app
undefined reference to `strlcat'
```

dasm 的 `src/errors.c` 在 `append_level` / `append_location` /
`append_information` **三处**无条件调用 `strlcat()`，项目内没有自带实现。

## 模式：`-include` 前置兼容头 + 宏改名

配方侧补桥，**不改上游源码、不删调用、不加源码补丁**：

```c
/* dasm_ohos_compat.h —— 由 conanfile 生成，经 -include 前置到每个编译单元 */
#ifndef DASM_OHOS_COMPAT_H
#define DASM_OHOS_COMPAT_H

#include <stddef.h>

size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz);
size_t dasm_compat_strlcpy(char *dst, const char *src, size_t siz);

#define strlcat dasm_compat_strlcat
#define strlcpy dasm_compat_strlcpy

#endif
```

```python
cflags = " -O2 -std=c99 -I." + ' -include "' + compat_h + '"'
self.run(f'cd "{src}" && {cc} {cflags} -c compat.c -o compat.o')
# …每个核心 .c 同样带 -include，链接时 compat.o 一起参与
```

### 为什么用宏改名，而不是 `#if defined(__GLIBC__)` 条件判断

在**已提供** `strlcat` 的 libc 上，`<string.h>` 里的原型会被一并改名成**同签名**的
自带实现，不会重复定义；在 musl 上则同时给出声明与实现。**一种写法覆盖两种 libc**，
不需要枚举 libc 家族、也不会因为 glibc 版本差异（<2.38 无 / ≥2.38 有）而写出错的分支。

### ★ 必须严格复刻 OpenBSD 返回值语义

这是最容易写错的一点。`strlcat` 在**截断时返回"拼接所需的完整长度"**，而不是
"实际写入长度"；`strlcpy` 返回 `strlen(src)`。调用方（dasm 的 `errors.c`）会把返回值
当作已写偏移继续推进，因此：

- 用 `strncat` 凑 → 偏移算错，后续写入落到错误位置；
- 用 `strncpy` 凑 → 不保证 NUL 结尾且返回 dst 指针，语义完全不同。

参考实现（OpenBSD 语义逐行复刻）：

```c
size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz)
{
    char *d = dst; const char *s = src;
    size_t n = siz, dlen;
    while (n-- != 0 && *d != '\0') d++;
    dlen = (size_t)(d - dst);
    n = siz - dlen;
    if (n == 0) return dlen + strlen(s);      /* ← 截断：返回“所需完整长度” */
    while (*s != '\0') {
        if (n != 1) { *d++ = *s; n--; }
        s++;
    }
    *d = '\0';
    return dlen + (size_t)(s - src);
}
```

## 验证证据（dasm 实测）

```console
$ nm -D pkg/bin/dasm | grep strl
                 U strlen
0000000000016c24 T dasm_compat_strlcat     ← 自带实现，无 UND strlcat
$ readelf -d pkg/bin/dasm | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]   ← 无额外运行时依赖
```

- 配方构建（OHOS clang）：通过
- 产物：`bin/dasm` 203552 B，ELF64 AArch64 PIE；`bin/ftohex` 16720 B
- test_package：**38 passed, 0 failed**（在真实 OHOS aarch64 制品上实跑）
- 上游套件：93 例 85 OK（8 项未通过均上游既有元测试/既知失败）

## 判据速查（适配前一条命令定性）

```console
$ grep -rn '\bstrlcpy\b\|\bstrlcat\b' src/
$ printf '#include <string.h>\nsize_t f(char*d,const char*s,size_t n){return strlcat(d,s,n);}' > t.c
$ clang -std=c99 -c t.c        # 报错/告警即说明本机 libc 没有
```

## 推广面

所有调用 BSD 字符串函数的软件适配到 OHOS 都可复用此模式。本条目补上了
"glibc 有 / musl 无"补齐库家族的一支，与以下条目同族：

- `DRAFT-argp-musl-gap-bridge`（argp-standalone）
- musl-fts / musl-obstack（glibc 缺、musl 有；反向家族）

另外相关但独立的两个交付链陷阱见
`DRAFT-conan-delivery-chain-silent-traps`。
