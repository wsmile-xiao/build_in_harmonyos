# locarna

## 简介

LocARNA（Local Alignment of RNA）是 Sebastian Will 等人开发的 RNA 序列与二级结构比对工具集：
基于 Turner 自由能模型，支持成对/多重、全局/局部 RNA 比对。核心为 C++ 库 `libLocARNA`，
上游同时提供一组命令行工具。源码以 autotools 构建（发布包自带预生成的 `configure` 与 `Makefile.in`）。

## 功能概述

本包交付 8 个原生 C++ 工具（`bin/`）：

| 工具 | 说明 |
|------|------|
| `locarna` | 成对（全局 + 局部）RNA 序列-结构比对，主工具 |
| `locarna_p` | 基于碱基对概率的成对/多重比对 |
| `exparna_p` | 期望精度（expected accuracy）成对比对 |
| `sparse` | 稀疏化多重结构比对（大输入可伸缩） |
| `locarnap_fit` | 由比对结果拟合比对参数 |
| `locarna_deviation` | 计算比对与参考结构之间的偏差 |
| `locarna_rnafold_pp` | RNAfold 后处理 |
| `ribosum2cc` | RIBOSUM 矩阵 → 相关系数转换 |

同时交付静态库 `lib/libLocARNA-2.0.a`、C++ 头文件（`include/LocARNA-2.0/LocARNA/*.hh`）与
`lib/pkgconfig/LocARNA-2.0.pc`。

## OHOS 适配

### 2.0.1（feat/locarna-2.0.1）

- **AArch64 `getopt_long` EOF 死循环（核心修复）**：上游 `src/LocARNA/options.cc` 的
  `process_options()` 用 `char c` 承接 `getopt_long()` 的 int 返回值。AArch64 的 plain `char`
  默认无符号（AAPCS / `__CHAR_UNSIGNED__`），EOF(-1) 截断为 255，主循环
  `while ((c = getopt_long(...)) != EOF)` 永不退出 → 任何调用（含 `--help`/`--version`）都
  100% CPU 空转、零输出、`timeout` 返回 124。补丁 `patches/0001-src-LocARNA-options.cc.patch`
  把接收变量改为 `int c`，8 个工具全部恢复正常（含真实成对比对）。
  定位手段：OHOS 沙箱禁用 ptrace（gdb/lldb 均不可用），改用 `LD_PRELOAD` 注入
  `ITIMER_PROF` + `SIGPROF` 采样器读 `ucontext_t.uc_mcontext.pc`，再由 `llvm-addr2line` 反查符号。
- **ViennaRNA 硬依赖**：`viennarna/2.7.2`（`RNAlib2 >= 2.5.1`）。其 `RNAlib2.pc` 的 `prefix=/`
  在 OHOS 会解析到宿主 `/lib`，配方在 `generate()` 中重写为 viennarna 包目录并注入
  `PKG_CONFIG_PATH`，使 `PKG_CHECK_MODULES([VRNA],[RNAlib2 >= 2.5.1])` 探测成功。
- **老版 config.sub（2014）不识别 ohos**：采用 libuuid 模式显式传
  `--build/--host=aarch64-unknown-linux-gnu`，autotools 永不直接收到 `ohos` 三元组。
- **HMDFS 构建修补**（构建期内容锚定、幂等）：`configure` 的 `umask 077`→`022`（临时目录否则不可写），
  `ac_pwd=\`pwd\`` 追加 `|| ac_pwd="$PWD"` 回退（getcwd 在沙箱内可能失败）。
- **`make install`** 经上游 bundled `config/install-sh`（由 `/bin/sh` 驱动）执行，绕过 OHOS 宿主
  `install` 包装器在多文件 pkginclude 批次上的 `Error 64`。
- **静态构建**：`--disable-shared`，交付静态 `libLocARNA-2.0.a`，规避 OHOS 共享库加载问题（R26）。
- **Perl 前端不交付**：`lib/perl` 的 `MLocarna.pm` 经 `MLocarna::threaded` 使用 `threads`，
  而 OHOS PC 镜像自带 Perl 未编译线程支持（`This Perl not built to support threads`）。
  因此禁用 `lib/perl` 子目录，并在 `package()` 中剔除 `bin/` 内的 23 个非 ELF 助手脚本
  （mlocarna、locarnate、`*.pl`、`RNAz.pm`、`benchmark-plot.R` 等），只交付可执行的 ELF 工具。
- **上游测试**：`make check` 只保留 Catch2 单元套件 `test_locarna_lib`（22 用例 / 175 断言，全通过）；
  集成驱动 `test_programs`（bash/perl）在 OHOS 不具备运行条件，已从 `TESTS` 剔除并在 PR 披露。
- 命令行工具集，已按 R38 声明 `commands.json`。

## 依赖关系

- 编译依赖：viennarna/2.7.2（`RNAlib2`，经 pkg-config）、clang/clang++、make
- 运行依赖：musl `libc.so`、libc++ 运行库（SDK 提供）；静态 `libLocARNA-2.0.a` **不内嵌** ViennaRNA（消费端须一并链接 viennarna 的 libRNA）

## 参考资料

- 项目主页：<https://s-will.github.io/LocARNA>
- 源码包：<https://github.com/s-will/LocARNA/releases/download/v2.0.1/locarna-2.0.1.tar.gz>
- 相关补丁：`patches/0001-src-LocARNA-options.cc.patch`（AArch64 plain char / getopt EOF 死循环）
