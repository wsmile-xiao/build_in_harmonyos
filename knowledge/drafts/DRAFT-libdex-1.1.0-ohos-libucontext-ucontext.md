# DRAFT — OHOS：libucontext 提供 ucontext 上下文切换（libdex 1.1.0）

**来源事件:** libdex 1.1.0 适配（执行端 pc1-4，2026-09-10）
**状态:** 草稿（待 promote 审核）
**对应 .kv:** `DRAFT-libdex-1.1.0-ohos-libucontext-ucontext.kv`

## 问题

在 OHOS PC (aarch64, musl) 上编译 libdex 1.1.0（GNOME 异步/fiber 库）时：

1. 编译 `src/dex-scheduler.c` 报：
   ```
   ../src/dex-fiber-context-private.h:108:3: error: call to undeclared function 'makecontext'
   ../src/dex-fiber-context-private.h:131:3: error: call to undeclared library function 'getcontext'
   ../src/dex-fiber-context-private.h:169:7: error: call to undeclared function 'swapcontext'
   ```
2. 独立最小验证：`ld.lld: error: undefined symbol: getcontext`（OHOS libc.so 无此符号）

OHOS musl-libc 的 `ucontext.h` 仅含 `struct __ucontext` 前向声明，**不提供**
makecontext/getcontext/swapcontext/setcontext 的声明与实现（musl 不实现传统
ucontext API）。libdex 的 fiber 调度器依赖它们做协程上下文切换。

## 根因

musl 有意不实现非 POSIX 的 ucontext 上下文切换函数族；OHOS musl 沿用该取舍，
头文件缺声明、libc.so 缺符号。上游 libdex 的 meson.build 只在 mips/OpenBSD 等
平台回退到 libtask 模拟（dex-ucontext-private.h），aarch64 Linux 分支默认假设
glibc/musl 提供 ucontext API——OHOS 恰好落空。

## 方案

外部依赖 `libucontext/1.5.2`（ohpcd 已发布 OHOS armv8 包）：
- `libucontext.a` 导出 `libucontext_makecontext`（+ `makecontext` **弱符号**）
- `libucontext_posix.a` 导出 `getcontext`/`setcontext`/`swapcontext` 强符号

1. conanfile.py：
   ```python
   if self.settings.os == "OHOS":
       self.requires("libucontext/1.5.2")
   ...
   if self.settings.os == "OHOS":
       self.cpp_info.system_libs += ["ucontext", "ucontext_posix"]
   ```
2. 源码补丁（0002）在 `__OHOS__ && HAVE_UCONTEXT_H` 分支补充 4 个 extern 声明
   （头文件无声明，-Werror=implicit-function-declaration 必须显式声明）。

## 验证

- `conan create`（ohos-aarch64 profile）G2 全绿，`test-fiber` PASS
- 专项测试 `test-ohos-fiber`：fiber 上下文切换 value=42、channel send/recv=200 全 PASS
- 链接参数：`-L<libucontext>/lib -lucontext -lucontext_posix`

## 适用边界 / 反例

- **适用**：OHOS 上依赖 makecontext/getcontext/swapcontext 做 fiber/coroutine 的 C 库
- **反例**：仅头文件含 `ucontext.h` 但不实际调用上下文切换函数的库无需依赖；
  Windows/msvc 平台（libdex 走 `G_OS_WIN32` fiber API）不需要
- **注意事项**：libucontext 的 `makecontext` 是弱符号，静态链接时需同时链
  `libucontext.a` 与 `libucontext_posix.a`；`ucontext_t` 对齐 ALIGN_OF_UCONTEXT=16
  按 aarch64 实测，其他架构需复核

## 查重记录

- E534（musl 缺 GNU 扩展函数）：触发（非 POSIX 函数族）、方案（源码 compat 填充）均不同，未命中
- E462（ucontext 信号帧调试）：仅关键词重合，主题不同，未命中
- 无既有 ucontext/libucontext 相关草稿，新增价值成立
