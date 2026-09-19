# safe-iop 0.3.1 HarmonyOS 适配笔记

## 编译环境

- 系统：HarmonyOS PC，aarch64/armv8，LP64
- 编译器：HarmonyOS SDK Clang 15.0.4
- Conan：2.29.1 OHOS 适配版
- 构建方式：使用 Conan profile 指定的编译器直接编译
- 第三方依赖：无

## 官方源码

- 项目归档：https://code.google.com/archive/p/safe-iop/
- 源码：https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/safe-iop/safe-iop-0.3.1.tgz
- SHA256：`96027e1512dc463f8418e0ba89f8c39a4bfe36cf2456c9afbf1b3897b4e9cf76`
- 上游许可：Public Domain

## 适配方法

上游 Makefile 没有安装目标，且 `CC = gcc` 是固定默认值。配方不修改上游源码，直接使用 Conan profile 中的 C 编译器编译 `src/safe_iop.c`，安装 `safe_iop.h` 和 `libsafe_iop`。非系统同名库默认构建共享库，同时保留 `shared=False` 的静态库选项。

`safe_iop.h` 的核心宏使用 GNU `typeof` 和 statement expression，消费者测试使用 `-std=gnu11`。库本身及测试在 OHOS musl 环境无需补丁。

## 上游测试清点（R51）

| 清点项 | 结果 | 证据 |
|--------|------|------|
| 独立 `tests/` 目录 | 0 | 源码包只有 `include/`、`src/`、`examples/`；测试嵌入 `src/safe_iop.c` |
| 官方测试入口 | 1 | Makefile 的 `test` 目标编译并运行 `safe_iop_test` |
| 注册测试组 | 73 | `main()` 中 73 个 `tests++` 调用 |
| 运行时断言 | 459 | `EXPECT_TRUE`/`EXPECT_FALSE` 的实测汇总 |

上游测试在未修改源码上分别完成了本地主机基线和 HarmonyOS PC 真机原生执行。HarmonyOS 实测结果：

```text
459/459 expects succeeded (0 failures)
73/73 tests succeeded (0 failures)
```

Conan 配方的 `build()` 会再次执行原始 `make test`，解析并强制核对上述两个汇总；任一数量变化或失败都会使 `conan create` 失败。

## 消费者与鸿蒙特有测试

- `test_safe_iop.c`：链接打包后的 `libsafe_iop`，执行 12 个始终有效的检查，覆盖五类运算、多操作数宏和 `safe_iopf` 导出符号。
- `test_safe_iop_ohos.c`：仅在 `os=OHOS` 时编译运行，编译期确认 `__OHOS__` 与 `__aarch64__`，并以 5 个检查验证 LP64 ABI 以及 `size_t`、`unsigned long`、`long` 边界溢出行为和 `safe_iopf`。

适配后共执行 75 个测试用例（73 个上游测试组、1 个通用消费者测试、1 个鸿蒙特有测试），共 476 个断言，未删减或修改上游测试。

## 结果

- 上游测试：73/73 测试组，459/459 断言通过。
- 新增测试：2/2 测试程序，17/17 断言通过。
- 补丁：无。
- 状态：`built`，等待 PR CI 发布验证。
