# DRAFT: strndupa 宏实现陷阱 — clang 内联 alloca 的 lifetime 失效

## 场景

OHOS musl-bionic libc 没有 `strndupa`（glibc 扩展）。移植使用了
`strndupa` 的老式 C 代码（如 libaudit 2.7.4 的
`auparse/auparse.c`、`src/ausearch-lol.c`、`src/auditd.c`）时需要自实现。

## 症状

用 `static inline` 函数实现 strndupa 后：

- 编译零警告、运行零崩溃；
- 但 strndupa 返回的字符串被后续“原地写”的解析函数
  （`audit_strsplit` 会把空格替换为 `'\0'`）处理后**内容损坏**：
  token 乱码（如 `type=LOGIN` 变成 `type=LOGIN msg=a<n...>`）；
- libaudit 的上游测试 auparse_test Test 1 输出与 .ref 对不上（14 行
  auid 输出全部缺失），Test 2 直接 "Error getting first record"。

## 根因

glibc 的 strndupa 是**语句表达式 + alloca 的宏**——缓冲存活于
**调用者的栈帧**，与调用者的其他局部变量同生共死。

而 `static inline char *strndupa(...)` 在 clang 下会被内联：内联器为
函数内的 `alloca` 插入 `llvm.lifetime.start/end` 标记，**函数返回点即
lifetime.end**。返回的指针指向被标记失效的栈内存；后续任何写入/读取
（尤其在 LTO/优化下栈槽被复用后）都是未定义行为——实测表现为静默
数据损坏。

最小复现（clang 15, aarch64-ohos）：

```c
static inline char *strndupa(const char *s, size_t n) {
    size_t len = strnlen(s, n);
    char *p = alloca(len + 1);
    memcpy(p, s, len); p[len] = '\0';
    return p;   // 内联后：alloca 缓冲在 return 处 lifetime.end
}
char *tmp = strndupa(b, 80);
char *tok = audit_strsplit(tmp);  // 原地写 '\0' → 踩失效内存 → 乱码
```

## 修复

用**宏**（语句表达式）实现，alloca 展开在调用点、缓冲归属调用者
栈帧——与 glibc 语义一致：

```c
#ifdef __OHOS__
#include <alloca.h>
#define strndupa(s, n) \
    (char *)({ const char *_s = (s); size_t _n = (n); \
       size_t _l = strnlen(_s, _n); \
       char *_p = __builtin_alloca(_l + 1); \
       memcpy(_p, _s, _l); _p[_l] = '\0'; _p; })
#endif
```

注意插在 `#include <string.h>` **之后**（宏体用到
strnlen/memcpy 的声明）。

守卫方式（R8 口径）：上游规则允许源码中 `#ifdef __OHOS__`（须有
实质逻辑），patches/ 中默认禁止但留有"无 POSIX 等价物"豁免通道。
strndupa 是 glibc 私有扩展，无 POSIX 等价物，AC_CHECK_FUNCS 也探测
不了宏缺失，故用 `__OHOS__` 守卫并在 PR 正文申报理由；更保守可改
`#if !defined(__GLIBC__)`。

## 验证

- 修复前：`auparse_test` Test 1 输出缺 14 行、Test 2 报错退出；
- 修复后：auparse_test 十段全部通过，diff 与上游
  `auparse_test.ref` 完全一致（"Auparse Test Passes"）。

## 适用面

任何“musl 系 libc 缺 glibc alloca 族扩展（strndupa/strdupa） +
clang 工具链”的移植。判定特征：inline 版本“看起来能跑”但下游
字符串解析静默损坏。
