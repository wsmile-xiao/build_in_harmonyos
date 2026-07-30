# SoftFloat 3e 适配笔记

## 编译环境

- 构建系统：上游 GNU Make 目标目录构建
- 编译日期：2026-07-20
- 编译器：OpenHarmony Clang（aarch64）
- 状态：built

## 编译步骤

1. 下载官方 `SoftFloat-3e.zip`，使用上游 `build/Linux-ARM-VFPv2-GCC` 的 Makefile 和平台 specialization。
2. 通过 Conan 配方从 `tools.build:compiler_executables` 取得编译器和归档器，使用 `-std=c99 -fPIC -DSOFTFLOAT_ROUND_ODD -DINLINE_LEVEL=5` 构建 `softfloat.a`。
3. 安装公开头文件至 `include/`，安装静态库为 `lib/libsoftfloat.a`。
4. 下载官方 `TestFloat-3e.zip`，将其 `testsoftfloat` 链接到本次构建的 SoftFloat 静态库，执行上游差分测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | 本机默认 Conan 不识别 `os=OHOS` | 初始环境安装的是官方 Conan 2.30.0 | 从鸿蒙社区源安装 OHOS 适配版 Conan 2.29.1，并重新初始化 Conan 环境。 |
| 2 | 上游 Makefile 的 `$@` 和变量被 shell 提前展开 | Conan `self.run()` 会经 shell 传递 Make 变量 | 在配方中转义 `$`，保留给 GNU Make 展开。 |

## 源码修改

未修改上游源码；配方复用了上游 ARM-VFPv2 specialization 及其 Makefile。

## 依赖版本

SoftFloat 和 TestFloat 均为官方 Release 3e；运行时和构建时没有 Conan 第三方依赖。

## 验证结果

```bash
conan create archives/s/softfloat/3e \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 官方 TestFloat 差分测试（在配方 build() 内执行）
testsoftfloat -seed 1 -level 1 -errorstop -all1
testsoftfloat -seed 1 -level 1 -errorstop -all2
```

Conan create、官方 TestFloat 一元与二元运算测试，以及 `test_package` 的 `f32_add` 消费者测试均通过。

## 注意事项

该包使用上游 ARM-VFPv2 specialization 的 NaN 和异常语义。下游如需与特定硬件或 ABI 严格一致的非默认 NaN 策略，应在调用端明确评估该语义。
---

**编译结束**: 2026-07-21 00:17
**最终状态**: built
