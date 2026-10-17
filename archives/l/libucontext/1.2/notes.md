# libucontext 1.2 HarmonyOS 适配笔记

## 目标与状态

- 目标：OHOS 6.0、aarch64（Conan `arch=armv8`）、clang 15。
- 构建系统：上游 Makefile；无第三方构建或运行依赖。

## 适配方案

配方从 Conan 的 `tools.build:compiler_executables` 读取 `clang`、`llvm-ar` 和 `llvm-ranlib`，将 `armv8` 映射为上游识别的 `ARCH=aarch64`。构建固定使用 `-j1`，并在打包前执行上游 `make check`。

上游同时构建静态库和共享库。配方依据 `shared` 选项删除另一种类型，避免默认静态包被链接器误选为共享库。上游安装规则没有创建 `libucontext_posix.so` 链接名，因此共享包在打包阶段补齐指向 `libucontext_posix.so.1` 的符号链接。1.2 的安装接口使用：

```text
make ... install DESTDIR=<package>/ LIBDIR=lib INCLUDEDIR=include PKGCONFIGDIR=lib/pkgconfig
```

`DESTDIR` 末尾的 `/` 不能省略，因为上游 Makefile 直接拼接目录变量。

## 测试与鸿蒙专项门禁

- 上游 `make check` 运行 3 个程序：核心上下文切换、裸 POSIX ABI、带信号掩码的 POSIX ABI。
- 通用 `test_package` 复用上游公开领域场景，验证两个上下文、10 个参数、`getcontext`/`makecontext`/`swapcontext`/`setcontext` 完整往返，并检查 API 返回值。
- OHOS 专项程序仅在 `CMAKE_SYSTEM_NAME` 为 `HarmonyOS` 或 `OHOS` 时构建，并用 `#ifndef __OHOS__` 阻止误跑。OHOS 的 `<ucontext.h>` 提供 `ucontext_t` 但不声明传统函数，因此测试显式声明由本包提供的未加前缀 ABI，并验证：子上下文实际执行、切换前后信号掩码恢复、超过 aarch64 8 个参数寄存器的 10 参数传递，以及 aarch64 SP 的 16 字节对齐。
- 两个消费者程序都由 Conan `self.run(..., env="conanrun")` 直接执行，不使用空测试或仅注册 CTest。

## CI 回归记录

- PR #7660 首轮 `conan-build-test` 在调用 SDK `lld` 时误加载系统
  `libxml2.so.16`；配方现从实际 clang 推导 SDK `llvm/lib`，探测通过后仅在
  构建和测试环境前置该目录。
- 后续 OHOS 6 aarch64 CI 中，上游 3 个 `make check` 程序、打包及消费者
  编译均通过；消费者运行到 `getcontext`/`setcontext` 往返时发现恢复后的
  `libucontext_getcontext()` 返回 context 指针并触发 abort。该结果对应 1.2
  aarch64 汇编缺陷，现由回移补丁修复。
- 修复后已在 Windows 使用 OHOS 6 armv8 profile 完成一次干净
  `conan create`：补丁导出与应用、静态库构建、安装、两个消费者程序的
  aarch64 交叉编译和链接均通过。aarch64 运行态结论等待远程 CI 复验。

## 源码修改与依赖

- 源码补丁：`0001-arch-aarch64-getcontext.S.patch`。1.2 的
  `getcontext.S` 先将保存的 `x0` 写为 0，随后又被传入的 context 指针覆盖；
  `setcontext` 恢复后会让原 `getcontext()` 返回非零。补丁回移上游 1.5.2
  的寄存器保存顺序，使初次返回和恢复后均返回 0。该问题由 OHOS 6
  aarch64 静态 Conan 消费者测试的完整往返检查发现；上游 1.2 自带测试
  未检查 API 返回值，因此未能捕获。
- Conan 依赖：无。
- 产物：`libucontext`、`libucontext_posix`、公开头文件及 pkg-config 元数据。

**编译结束**: 2026-09-02 11：41
**最终状态**: built
