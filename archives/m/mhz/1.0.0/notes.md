# mhz 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，`CC := gcc`）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang（Conan profile 的 `tools.build:compiler_executables.c`）
- 状态: built

## 编译步骤

1. 从官方 `codeload.github.com` 取 tag `v1.0.0` 的源码包（`mhz-1.0.0.tar.gz`）。
2. `build()` 执行 `make CC=<ohos clang> -j1`，产出 `mhz`。
3. `package()` 安装 `bin/mhz`、`licenses/{LICENSE,README.md}`。
4. `test_package/test_mhz.sh` 运行 5 项检查（存在性、`-h` 用法、`-c` 测量输出为数字）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CC := gcc` 硬编码 | Makefile 立即赋值默认 gcc | 命令行 `make CC=<clang>` 覆盖立即赋值，无需补丁 |
| 2 | rdtsc 是否可用 | `HAVE_RDTSC` 仅在 `__i386__/__x86_64__` 定义 | aarch64 走 `CLOCK_MONOTONIC`，`rdtsc()` 展开为 0；`-t` 选项随之不出现，编译运行均正常 |

## 源码修改

无。零补丁。

## 依赖版本

无三方依赖（仅 libc）。

## 验证结果

```bash
# 消费者（test_package/test_mhz.sh，5 项）
MHZ_CHECK_SUMMARY checks=5 fails=0
```

## 注意事项

- 上游无测试套件，按 §3.6 口径声明上游 N=0，另加鸿蒙特有（消费者）测试 5 项。
- `mhz -c` 只测量 CPU 频率（不依赖 rdtsc），输出单个数字；消费者据此断言。
