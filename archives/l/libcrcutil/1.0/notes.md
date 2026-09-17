# libcrcutil 1.0 适配笔记

## 编译环境

- 构建系统：CMake 适配构建（上游源码）
- 编译日期：2026-09-14
- 目标：OHOS 6.0 / AArch64
- 编译器：OHOS Clang 15.0.4，C++17/libc++
- 状态：built

## 编译步骤

1. 从 Google Code Archive 官方归档地址下载 `crcutil-1.0.tar.gz`，校验
   SHA-256 为 `87f0448c235d195c8df2a834ec7c24613f62878500468ff3aeb2dab2b10ffcf1`。
2. 应用非 x86 测试源码修复，生成自包含 CMake 构建描述，避免运行时自举
   Autotools。
3. 使用 Conan OHOS AArch64 profile 构建静态或共享 `libcrcutil`。
4. `build()` 内通过 CTest 运行上游 `crcutil_ut --noperf`，随后构建并执行三个
   安装后消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AArch64 编译器拒绝 `-msse2` | 上游 Makefile 无条件启用 x86 SSE2/SSE4 编译选项 | 移除固定 x86 选项，以 `platform.h` 的架构特征检测选择实现，并默认使用可移植 CRC32C 路径 |
| 2 | 上游只构建测试和 `/tmp/usage`，不产出可安装库 | 1.0 发布包没有库目标且硬编码只读临时路径 | 使用自包含 CMake 构建描述构建并安装真实库与公共头文件 |
| 3 | OHOS Clang 编译上游测试失败 | 非 x86 分支缺少依赖基类限定，并引用 x86 专用 `Crc32cSSE4` 类型 | 使用 `this->Init`，并以现有 `HAVE_AMD64/HAVE_I386` 特征宏保护 x86 类型引用 |
| 4 | AArch64 无 x86 `RDTSC`，默认性能段没有有效计时数据且耗时极长 | 上游 `Rdtsc::Get()` 在非 x86 明确返回 0 | 由 CTest 使用上游支持的 `--noperf` 运行全部功能场景；性能基准不是独立测试用例 |
| 5 | CI Worker 缺少 `aclocal`，无法运行 `autoreconf` | 原配方在构建时依赖 Worker 全局 Autotools 状态 | 改用仓内同类项目已验证的自包含 CMake 构建模式，彻底移除 Automake/Libtool 构建依赖 |

## 源码修改

- `0001-fix-non-x86-unit-tests.patch`：修正上游测试在非 x86/现代 Clang 上的编译。
- 配方生成最小 CMake 构建描述：编译上游真实库源码和原始测试入口，安装公共头文件，
  并以 CTest 注册完整功能套件。

## 依赖版本

- 无第三方运行时或 Conan 依赖。
- 构建工具：CMake、Conan 2.29.1。

## 测试计数与结果

- 上游在 AArch64 上由源码条件实际注册 54 个功能场景，全部通过（54/54）。
- 上游在 x86_64 上受 `MAX_FACTORY_COUNT=100` 限制实际执行 100 个功能场景，
  全部通过（100/100）；额外部分为 x86 SSE2/CRC32C 专用场景，不适用于 AArch64。
- 上游 Automake 聚合入口为 1 个；场景数按日志中独立的
  `Functional test of ...` 条目计数，不把 Byte/Word 等内部算法断言重复计作测试。
- 新增安装后通用消费者测试 1 个、45 个独立 CRC32C 向量场景、HarmonyOS
  AArch64 专项测试 1 个，均通过（47/47）。
- 适配后独立测试总数 101，不少于上游 x86_64 实测 100；其中上游在目标
  AArch64 上适用的 54 个功能场景全部保留并通过。

## 验证结果

```text
Language preflight: cpp — PASS
CTest upstream functional (OHOS AArch64): 54/54 — PASS
test_package: 47/47 — PASS
conan create: PASS
repository gates: PASS
```

## 注意事项

- 不使用 `__OHOS__` 修改生产代码；架构选择沿用上游 `HAVE_*` 特征宏。
- `--noperf` 仅关闭无有效 AArch64 计时源的性能基准，不删除、跳过或弱化任何
  上游功能场景及断言。
---

**编译结束**: 2026-09-14 11:16
**最终状态**: built
