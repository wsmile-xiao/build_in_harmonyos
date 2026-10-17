# DRAFT-librope-1.0.0-ssize-t-sys-types-h — OHOS 上按名使用 ssize_t 的 C 翻译单元需显式包含 <sys/types.h>

> **Contributor**: pc2-35 | **Status**: DRAFT | **Updated**: 2026-09-27
> **Severity**: medium | **Category**: headers / portability / ohos / libc / compat / posix / c99
> **Audience**: 任何在 OHOS 上用 clang -std=c99 编译、直接使用 ssize_t 的 C/C++ 三方库
> **Stem**: DRAFT-librope-1.0.0-ssize-t-sys-types-h（与同名 .kv 配对，字段逐一对齐）

## 问题（Symptom）

librope 1.0.0（纯 C UTF-8 rope 库，raw Makefile）在 OHOS aarch64 上用 clang `-std=c99` 编译报：

```text
rope.c:252:8: error: unknown type name 'ssize_t'; did you mean 'size_t'?
  static ssize_t bytelen_and_check_utf8(const uint8_t *str);
rope.c:475:3: error: unknown type name 'ssize_t'; did you mean 'size_t'?
  ssize_t num_inserted_bytes = bytelen_and_check_utf8(str);
rope.c:169:44: warning: call to undeclared function 'random'; ISO C99 and later do not support implicit function declarations
```

## 根因（Root Cause）

`ssize_t` 是 POSIX 带符号字节数类型（定义于 `<sys/types.h>`），不是 ISO C 标准类型。glibc 会通过 `<stdlib.h>`/`<string.h>` 等常用头传递引入 `<sys/types.h>`，所以上游 C 代码在 Linux 上按名使用 `ssize_t` 不报错；OHOS 的 musl 系 libc 头文件不做这种传递包含，加上 `-std=c99` 下 clang 强制 ISO C（禁止隐式类型/隐式函数），按名使用 `ssize_t` 的翻译单元即报 unknown type name。`random()` 的 implicit-function-declaration 属同类：上游依赖 glibc 传递提供 `<stdlib.h>` 声明，OHOS musl 不传递。

属于平台头文件传递性差异，非代码逻辑错误，也非本项目构建配置错误。

## 方案（Solution）

在使用 `ssize_t` 的翻译单元显式添加 `#include <sys/types.h>`（普适 POSIX 头，非平台宏，不引入 `__OHOS__` 分支），一行最小补丁：

```c
#include <stdlib.h>
#include <string.h>
#include <sys/types.h> // ssize_t (not pulled in transitively on OHOS musl)
```

librope 实测：补丁后 `make -j1` 通过（仅保留 random 隐式声明 warning，非阻断），`make tests && ./tests` 全部 PASS，`conan create` 干净重建通过。

## 验证（Validation）

- 编译：`make CC=clang -j1` → 仅 1 个非阻断 warning（random 隐式声明），产出 `librope.a`
- 上游测试：`make tests && ./tests` → `Normal tests passed. Running randomizers... Done!`（RC=0）
- Conan 干净重建：`conan create ... -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing` → G2 PASS（含 test_package 真实 API 回读测试）
- 补丁哈希：`patches/0001-rope.c.patch`（+1/-0，仅一行 include）

## 适用边界（Applicability）

- 适用于任何 OHOS 上按名使用 `ssize_t`（或依赖 glibc 传递包含提供 POSIX 名字）的 C 翻译单元
- 与 DRAFT-bbhash-1.0.0-u-int64-sys-types-h 同根因族（OHOS musl 不传递提供 BSD/POSIX typedef），但错误签名不同（`u_int64_t` vs `ssize_t`），互不等价
- 不适用于 C++ 翻译单元（应包含 `<sys/types.h>` 或使用 `<cstdint>` 系标准名）

## 反例与限制（Counterexamples / Limits）

- 若项目 Makefile 使用 `-Werror`，random 隐式声明 warning 会升级为 error，需同时显式声明或包含 `<stdlib.h>`（上游实际已包含，OHOS 下需验证声明可见性）
- 不适用于需要负返回值的严格 typedef 语义场景下的粗暴 `size_t` 替换（见 fallback 说明）

## 查重差异（Dedup）

- 正式库 E063（-Werror 禁 implicit-function）、E190/E194/E208（sys/types.h **file not found**，缺头文件路径类）、E032/E033（DIR/cchar_t）、E113（u_int/u_long/caddr_t）、E284（u_int16_t+config host）、E290（__kernel_*）、E367（Dl_info）均不覆盖 `ssize_t` 签名
- 草稿 DRAFT-bbhash-1.0.0-u-int64-sys-types-h 覆盖 `u_int*` 系，签名不同，互不等价
- 结论：无等价命中，新增本草稿（路径 B）
