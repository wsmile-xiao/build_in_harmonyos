# DRAFT-ohos-ucontext-decl-compat — OHOS musl 补 ucontext 族函数声明

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / musl / ucontext / fiber

## 相关既有条目（同族差异化定位）

本 skill 与既有 "musl libc 缺失" 条目共享 OHOS musl 兼容层背景，但本条目是
**ucontext 族函数声明缺失**（musl 声明了类型但未声明函数，实现需链 libucontext）——
非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E081**（secure_getenv） | 正式收录 | musl 无 secure_getenv（单函数，可降级） | 非本题——那是**单函数**且可降级 getenv；本条目是 **ucontext 族**（getcontext/makecontext/swapcontext/setcontext），类型已定义、函数未声明，实现需链 libucontext |
| **E085/E127**（pthread 取消族） | 正式收录 | musl 无 pthread_cancel 族 | 同族（函数族缺失），但**符号族不同**——pthread 取消 vs ucontext 栈切换 |
| **DRAFT-ohos-mqueue-stub**（本批 systemd） | 草稿 | mq 族函数缺失（stub ENOSYS） | 同族（函数族缺失 stub），但**修法不同**——mq 无运行时只能 stub（ENOSYS）；ucontext 有 libucontext 实现（OHOS 有用户态栈切换库），只需补**声明** + 链库，不需 stub |
| **E203**（getprogname） | 正式收录 | musl 无 getprogname | 非本题——单函数 |

> 全库查证（2026-09-03）：`ucontext`/`getcontext`/`makecontext`/`swapcontext`/
> libucontext 声明缺失命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS 上编译、使用 ucontext 栈切换原语（fiber/coroutine 基础）的库时，若出现：

- `call to undeclared function 'getcontext'`（fiber.c 的 `getcontext(&uc)`）；
- `call to undeclared function 'makecontext'`（`makecontext(&uc, ...)`）；
- `call to undeclared function 'swapcontext'`（`swapcontext(&old_uc, &uc)`）；
- 已确认 OHOS musl `<ucontext.h>` 定义了 `ucontext_t` 类型但未声明这些函数。

典型实例：systemd/261（sd-future/fiber.c）。

## Symptom

```text
fiber.c:228: error: call to undeclared function 'getcontext' with type
  'int (ucontext_t *)' (aka 'int (struct ucontext *)')
fiber.c:241: error: call to undeclared function 'makecontext'
fiber.c:246: error: call to undeclared function 'swapcontext'
```

## Root Cause

1. glibc 的 `<ucontext.h>` 声明 getcontext/makecontext/swapcontext/setcontext
   （用户态栈切换原语）；
2. OHOS musl 的 `<ucontext.h>` **只定义 `ucontext_t` 类型**（及相关 struct），
   **不声明**这四个函数——musl 声明了 ucontext 相关类型但未实现函数；
3. 使用它们的库（systemd 的 sd-future/fiber.c）编译报 `call to undeclared function`。

## Recommended Solution

**主方案：musl 兼容头补函数声明 + 依赖链加 libucontext。**

- `src/include/musl/ucontext.h`：`include_next <ucontext.h>` 后补四个函数声明
  （`ucontext_t` 类型已由 musl 头定义）；
- **实现不在此提供**——依赖链加 `libucontext`（conan 依赖 + meson 的
  `-lucontext` 链接），因为 musl 声明了这些函数但未实现，libucontext 提供
  aarch64 用户态栈切换实现。

```c
int getcontext(ucontext_t *ucp);
int setcontext(const ucontext_t *ucp);
void makecontext(ucontext_t *ucp, void (*func)(void), int argc, ...);
int swapcontext(ucontext_t *oucp, const ucontext_t *ucp);
```

**回退方案**：若补声明+链库不可行，patch 源码关闭 fiber 特性——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前 fiber.c 报 getcontext/makecontext/swapcontext 未声明；补声明 + libucontext 依赖后编译链接通过，conan create 通过 |

## 测试覆盖边界

- 补声明只影响 **编译期**（让 fiber.c 看到函数原型）；链接期由 libucontext 提供
  实现，语义与 glibc ucontext 一致；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。
