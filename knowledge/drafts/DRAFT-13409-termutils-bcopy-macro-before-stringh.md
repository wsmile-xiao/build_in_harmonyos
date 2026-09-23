# E-DRAFT: bcopy→memcpy 兼容宏必须定义在 `#include <string.h>` 之后

- **触发实例**：termutils 2.0 适配（2026-09-13，任务 13409，分支 feat/termutils-2.0）
- **错误签名**：`error: conflicting types for 'memcpy'` + `note: expanded from macro 'bcopy'`
- **类别**：legacy-source-compat（老源码与现代 libc 头文件组合）
- **严重度**：2（编译期确定性失败，修复模式固定）

## 症状

clang 编译 1995 年代 GNU C 源码时：

```text
In file included from tparam.c:30:
.../sysroot/usr/include/string.h:57:   → strings.h:17:6:
error: conflicting types for 'memcpy'
void bcopy (const void *, void *, size_t);
     ^
tparam.c:25:24: note: expanded from macro 'bcopy'
#define bcopy(s, d, n) memcpy ((d), (s), (n))
                       ^
string.h:25:7: note: previous declaration is here
void *memcpy (void *__restrict, const void *__restrict, size_t);
```

## 根因

tparam.c 第 23-26 行：

```c
#if defined(HAVE_STRING_H) || defined(STDC_HEADERS)
#define bcopy(s, d, n) memcpy ((d), (s), (n))
#endif

#ifdef STDC_HEADERS
#include <stdlib.h>
#include <string.h>   /* ← 宏已生效，污染此后的系统头解析 */
```

OHOS musl sysroot 的 `<string.h>` 会再拉入 `<strings.h>`，后者声明真实函数
`void bcopy(const void *, void *, size_t)`。由于 bcopy 对象宏此时仍在作用域，
整条声明被宏展开成 `void memcpy((const void *), (void *), size_t)`，与
`string.h` 第 25 行的真实 `memcpy` 原型冲突 → 编译失败。glibc 主机上两头的
声明排布不同，同份代码往往能编过，因此该问题只在 musl 系平台暴露。

## 最小修复（平台无关）

把系统头 include 挪进同一个条件块、置于宏定义**之前**：

```c
#if defined(HAVE_STRING_H) || defined(STDC_HEADERS)
#include <string.h>   /* 先让系统声明可见 */
#define bcopy(s, d, n) memcpy ((d), (s), (n))
#endif
```

- 重复 include 无害（include guard）；
- 系统 `bcopy` 声明先于宏被解析；
- 包内所有 `bcopy(...)` 调用点在宏作用下依旧展开为 `memcpy`，全平台行为一致。

已验证：补丁后 termutils 2.0 在 OHOS aarch64 上 `conan create` 干净构建通过
（conan-verify G0-G4/L2/L4/L5 全绿）。

## 禁忌

- 禁止用 `#ifdef __OHOS__` 守卫补丁（R8/PF5 平台宏红线）；
- 禁止 `#undef bcopy` 之后重定义一类绕路写法；
- 禁止改 sysroot 头文件或改调用点改名。

## 适用范围与查重

- **适用**：任何以兼容宏遮蔽 BSD 字符串函数（bcopy/bcmp/bzero）且宏定义先于
  系统头包含的老 C 包（termutils、sharutils、cpio 等同代 GNU 包常见写法）。
- **查重**：knowledge/graph 现有 E001+ 条目与 drafts 中无 bcopy/memcpy 冲突
  模式（grep bcopy 零命中），本条目为新增。
