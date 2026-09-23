# minicoro

Single-file header-only asymmetric stackful coroutine library for C, by Eduardo
Bart (edubart). API inspired by Lua coroutines; designed as a coroutine backend
for the Nelua language.

- 官方仓库: https://github.com/edubart/minicoro
- 版本: 0.1.3 (2022-01-27 tag)
- License: MIT / Unlicense (双许可，随包分发 LICENSE)
- 语言: C (C89 兼容，`minicoro.h` 单头文件)

## 特性

- 非对称栈式协程，支持嵌套（协程内 resume 另一协程）
- 自定义分配器、自定义栈大小、storage 传值系统
- 实现自动选择：aarch64/x86/ARM/riscv 使用专用汇编（MCO_USE_ASM），
  其他平台回退 ucontext / fibers
- 无外部依赖（仅 libc；多线程示例额外依赖 pthread）

## OHOS 适配要点

- header-only：配方只安装 `include/minicoro.h`，不产生库二进制
- 消费者必须且仅在一个翻译单元定义 `MINICORO_IMPL` 再 include 头文件
- OHOS aarch64 下 `minicoro.h` 自动走 `__aarch64__` 汇编实现分支，
  无需源码补丁
- 上游测试由 `tests/Makefile` 驱动（testsuite/example/simple/mt-example/benchmark）

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.1.3 | built | header-only 适配，OHOS Conan 消费者测试通过 |

详见各版本目录下 manifest.yaml / notes.md。
