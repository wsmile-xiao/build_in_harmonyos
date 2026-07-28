# lp_solve 5.5.2.14 适配笔记

## 当前 Conan 积分赛适配（2026-07-27）

- Source: official GitHub `5.5.2.14` source release.
- Source SHA-256: `a4bbdc881128bdbe920a38e134c9add5db47f9aa814a0a018ba940b0f3c278c3`.
- The upstream `ccc` scripts identify the authoritative source set and
  preprocessor definitions. The recipe generates an equivalent CMake build so
  Conan controls the compiler, linker, build type, and target architecture.
- No source patch is applied. The historical patch files already present in
  this archive entry are not referenced by `conandata.yml` and are not part of
  the Conan source path.
- The package exports `liblpsolve55`, the `lp_solve` command, the complete
  header tree, and the upstream license.
- The exact source archive has no formal upstream test/check/regression
  runner; its `demo` directory is not counted as an upstream test suite.
- The consumer test solves a deterministic model and checks the optimum and
  variables. Its fault mode requires `read_LP` to reject a missing file.

## 历史预编译包记录（2026-06-09）

以下内容来自原有归档，仅用于保留旧流程背景，不作为本次 Conan
积分赛提交的测试或设备证据。

### 编译环境

- 构建系统: custom（自定义 Makefile，原始使用 ccc shell 脚本）
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 链接器: GNU ld.bfd 2.45
- 平台: OpenHarmony aarch64 (HongMeng Kernel 1.12.0)
- 状态: published

### 编译步骤

旧流程为 OpenHarmony 创建完整 Makefile：

1. 手动处理含嵌套 `lp_solve/lp_solve/` 目录的源码包。
2. 根据 `lpsolve55/ccc` 和 `lp_solve/ccc` 编写 Makefile。
3. 使用 `CC=clang CFLAGS="-fPIC -O2"` 及 GNU ld.bfd。
4. 构建 `liblpsolve55.a`、`liblpsolve55.so` 和 `lp_solve`。
5. 安装、打包并验证预编译产物。

### 历史问题与处理

| # | 问题 | 根因 | 历史处理 |
|---|------|------|----------|
| P1 | init-build 解压失败 | tarball 含同名嵌套目录 | 手动提升子目录内容 |
| P2 | 无标准构建标记文件 | 上游只提供 `ccc` 脚本 | 创建适配 Makefile |
| P3 | Flex/Bison 前缀不匹配 | 生成代码使用 `lp_yy*` 前缀 | 增加预处理映射 |
| P4 | Bison token 定义缺失 | include 顺序不满足生成头文件 | 增加 token 条件定义 |
| P5 | 旧环境中的 lld 不可用 | 缺少其运行时依赖 | 旧流程改用 GNU ld.bfd |
| P6 | 头文件安装不完整 | 仅安装少量公共头文件 | 扩展安装头文件集合 |

### 历史源码修改

- `0001-Makefile.patch`
- `0002-lp_rlp.h.patch`（后由 0003 替代）
- `0003-lp_rlp_tokens.h.patch`

这些文件保留在归档中，但当前 `conandata.yml` 不引用它们。

### 历史交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lp_solve-5.5.2.14-ohos-aarch64.tar.gz | 2219 KB | 旧预编译包 |
| lp_solve-5.5.2.14-ohos-aarch64-debug.tar.gz | 735 KB | 旧 Debug 符号包 |
