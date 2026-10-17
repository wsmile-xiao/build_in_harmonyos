# `rep_memset_s` 悬空符号：为什么不能补编 replace.c，以及 compat 桩怎么写

> Draft: DRAFT-TEVENT-0171-VENDORED-REP-MEMSET-S-STUB
> Stem: `tevent-0.17.1-vendored-rep-memset-s-stub` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-TEVENT-0171-VENDORED-REP-MEMSET-S-STUB
- **严重度**: 2
- **类别**: platform|portability|replace-layer|packaging
- **触发工具**: conan|clang|ld|make|configure
- **阶段**: compilation|link|packaging

## 错误特征

链接期：

```
ld.lld: error: undefined symbol: rep_memset_s
>>> referenced by tevent_signal.c
>>>               tevent_signal.o:(tevent_common_add_signal) in archive libtevent.a
```

按直觉补编 `lib/replace/replace.c` 之后，立刻变成一串与本事无关的报错：

```
lib/replace/system/network.h:31:2: error: "AC_LIBREPLACE_NETWORK_CHECKS missing in configure"
lib/replace/replace.c:64:2:  error: "you must have a ftruncate function"
lib/replace/replace.c:136:7: error: incomplete definition of type 'struct tm'
```

## 根因分析

`replace.h:994` 有 `#define memset_s rep_memset_s`。tevent 里没有任何一处
直接写 `memset_s`，但对 `ZERO_STRUCT` / `BURN_DATA` 这类便利宏来说这是
隐式依赖——它们在 `tevent_signal.c`、`tevent_epoll.c` 中展开，于是
`rep_memset_s` 成为归档里唯一的 replace 层未定义符号。

上游唯一实现位于 `lib/replace/replace.c:960`。但 `replace.c` 不是
一个普通源文件，它是 **waf 生成的全量 `config.h` 的配套一次性兼容层**：

| 依赖 | 未满足时的表现 |
|------|----------------|
| `AC_LIBREPLACE_NETWORK_CHECKS` | `#error` 硬失败 |
| `HAVE_FTRUNCATE` | `#error "you must have a ftruncate function"` |
| 完整 `struct tm` | `replace.h` 只做前向声明 → incomplete type |

也就是说，"把 replace.c 也编进去"会把一个**单符号**问题放大成
**构建系统**问题：必须伪造整份 autoconf 特性矩阵才能推进，而 tevent
真正需要的只是 `rep_memset_s` 一个函数。反过来，任何为了绕开 waf
而手写宏集合的移植（`-DNO_CONFIG_H`）都注定要面对这个落差。

## 解决方案

**主方案**: single-symbol-vendored-compat-object

在 version 目录下建 `files/tevent_ohos_compat.c`，只导出 `rep_memset_s`，
语义与上游逐行对齐：

```c
int rep_memset_s(void *dest, size_t destsz, int ch, size_t count)
{
    volatile unsigned char *cursor;

    if (dest == NULL) {
        return EINVAL;
    }
    if (destsz > (SIZE_MAX >> 1) || count > (SIZE_MAX >> 1) || count > destsz) {
        cursor = (volatile unsigned char *)dest;
        while (destsz-- != 0) { *cursor++ = (unsigned char)ch; }
        return ERANGE;          /* 注意：越界时仍按 destsz 清零，与上游一致 */
    }

    cursor = (volatile unsigned char *)dest;
    while (count-- != 0) { *cursor++ = (unsigned char)ch; }
    return 0;
}
```

三个不能省的细节：

1. **`RSIZE_MAX` 取 `SIZE_MAX >> 1`**（上游在那个分支里就是这么定义的），
   不是 `RSIZE_MAX` 的某个"标准值"；
2. **`ERANGE` 分支要先清零再返回**——上游是先 wipe `destsz` 字节再返回
   `ERANGE`，直接 return 会改变行为；
3. **必须用 `volatile` 指针写入**（或等价内存屏障）。上游在
   `HAVE_GCC_VOLATILE_MEMORY_PROTECTION` 分支里放了一条
   `__asm__ volatile("" : : "g"(dest) : "memory")`，目的就是防止编译器
   把这段清零优化掉。`BURN_DATA` 擦的是口令/密钥，被优化掉是安全问题，
   不是纯粹的行为差异。

打包方式：`exports_sources = "files/*"`，编译成独立 `.o` 后归档进库。
这与仓库中 `archives/t/talloc/2.4.4/files/talloc_compat.c` 完全同构——
Samba 家族三件套应统一用这一范式，不要各写各的。

## 验证

```sh
llvm-nm -u libtevent.a | grep rep_        # 无输出即满足
llvm-nm --defined-only tevent_ohos_compat.o
# 0000000000000000 T rep_memset_s
```

CI 中 `conan create archives/t/tevent/0.17.1` 的 `build()` 会编译该
compat 文件并运行两个上游 cmocka 单测（5 + 24 个用例）；`test_package`
另建管道 fd + timer + immediate 消费者测试，验证事件循环真实收敛。

## 关联条目

- 与 `sys_errlist` 条目同批：两者都是 `replace.h` 宏展开引出的隐式依赖，
  且都只在直连编译器（不跑 waf/config.h）时暴露；
- `archives/t/talloc/2.4.4/files/talloc_compat.c` 是本范式的既有先例，
  本条目把它推广到"只补一个符号、其余全部丢弃"的最小形态。
