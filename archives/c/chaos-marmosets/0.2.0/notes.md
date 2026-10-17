# chaos-marmosets 0.2.0 鸿蒙适配笔记

## 适配概述

- **适配平台**: HarmonyOS PC (aarch64)
- **编译器**: clang 15.0.4 (Target: aarch64-unknown-linux-ohos)
- **构建系统**: Makefile（原生）
- **适配类型**: 基础适配（路径 A）

## 主要修改

### 1. Makefile 适配
- 编译规则中 `$^` → `$<`，修复 clang 对多输入文件的处理
- 添加 `-pipe` 编译选项，兼容只读 `/tmp` 目录

### 2. Conan 配方
- 使用 `package_type = "application"`
- 通过 `exports_sources` 导出源码，使用 `self.run("make divide-by-zero leak-memory seg-fault")` 构建
- 产物安装到 `bin/` 目录

### 3. 测试适配
- `test_package/test.c` 通过 `fork` + `exec` 实际执行被测二进制
- `divide-by-zero` 预期退出码: 0（鸿蒙平台无 SIGFPE）
- `seg-fault` 预期退出码: 1（鸿蒙平台段错误返回 1）

### 4. commands.json
- 位于 `archives/c/chaos-marmosets/commands.json`
- 声明了三个 CLI 工具及其描述

## 平台差异

| 行为 | Linux (glibc) | HarmonyOS (musl) |
|------|---------------|------------------|
| divide-by-zero | SIGFPE，返回 136 | 返回 0，正常退出 |
| seg-fault | SIGSEGV，返回 139 | 返回 1 |

## 验证结果

- 编译状态: ✅ 通过
- Conan 验证: ✅ 全部门禁通过
- 测试通过率: 100%

## 已知限制

- `leak-memory` 程序运行可能因内存压力导致系统不稳定，已从自动化测试中排除，可手动验证

## 审查意见说明

### leak-memory.c 未检查 malloc 返回值
上游代码**故意**不检查 `malloc` 返回值，以实现"持续分配直到内存耗尽"的混沌测试语义。这是程序的设计目标，**不属于缺陷**，适配时保持上游原样。

### Makefile 默认目标调整
将 `all` 目标从 `divide-by-zero leak-memory seg-fault doc` 改为 `divide-by-zero leak-memory seg-fault`，避免默认构建时依赖 `pandoc`（CI 环境无此工具）。`doc` 保留为独立可选目标，需要时手动执行 `make doc`。

### test.c seg-fault 退出码
鸿蒙平台上 `seg-fault` 可能以退出码 1 正常退出，也可能被 SIGSEGV 信号终止。测试改为同时接受这两种崩溃行为，避免因平台差异导致误判。
