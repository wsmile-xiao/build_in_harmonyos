# Portable C Compiler (pcc) — OpenHarmony 编译档案

## 软件简介

pcc（Portable C Compiler）是一个轻量级、可移植的 C 编译器，由 Anders Magnusson
与 Ian Harvey 维护。它体积小、依赖少、代码结构清晰，历史上被广泛用于教学与
嵌入式/复古平台开发。

## 功能概述

- C89/C99 子集编译
- 独立的预处理器（`pcpp`）、编译器后端（`ccom`）、驱动（`pcc`）
- 支持 16 种目标架构后端：amd64、arm(32 位)、hppa、i386、i86、m16c、m68k、
  mips、mips64、nova、pdp10、pdp11、pdp7、powerpc、sparc64、vax
- 可变目标：同一个可执行文件可以通过 `-target`（或配置时的 `--target`）选择后端

## OHOS 适配

- **形态**：pcc 没有 aarch64 后端（`arm` 是 32 位），本包把它适配为**运行在鸿蒙 PC
  上的编译器**，配置时显式 `--target=amd64-linux`，默认生成 x86-64 代码
  （与已合入的 chibicc 同构）。若需要「在鸿蒙上产出 aarch64 机器码」，那要用
  clang/llvm 工具链，属另一个任务。
- **host 识别**：不传 `--host`，改由 `config.guess` 原生识别。上游自带的
  config.guess（2014-11-04）不认识 HarmonyOS，直接报
  `unable to guess system type`；补丁 `0001` 为其增加 HarmonyOS 分支，并让
  config.sub 接受 `linux-ohos`。
- **临时目录**：鸿蒙 `/tmp` 是 erofs 只读挂载（知识库 E002）。驱动原先把中间文件
  硬编码写到 `/tmp/ctm.XXXXXX`，除 `-E` 外任何编译都会失败；补丁 `0002` 让
  `gettmp()` 遵循 `$TMPDIR`。
- **x87 内联汇编**：`arch/amd64/code.c` 顶部的 `fstcw`/`fldcw` 在 aarch64 主机上
  编不过，补丁 `0003` 将其限定到 x86 主机。
- **`-fcommon`**：老式 tentative definition（`lineno` 等），现代 clang 默认
  `-fno-common`，去掉即 `duplicate symbol`。
- **静态链接**：产出静态 ELF，便于在被测平台之外执行（绕开 E544）。
- **已知平台行为**：鸿蒙 `/bin/install` 是 toybox，`install -s` 被静默忽略，
  因此安装后的二进制不带符号表剥离；这是上游 `INSTALL_PROGRAM = ${INSTALL} -s`
  在本平台的实际效果，配方不再额外处理。

## 依赖关系

- 运行时依赖：无
- 构建依赖：无（仅需 autotools、bison、flex 与平台 clang）

## 测试

- 上游测试：`cc/cpp/tests/`，由 `make -C cc/cpp test` 驱动，对 `test1`…`test18`
  比对 `res1`…`res18`，另有 `res15C`/`res16C` 两个 `-C` 变体，共 **20 次比较**
  （注意该目标用 `;` 串联比较，失败也返回 0，配方在 `build()` 中重新判定）
- 本机实测（真机原生执行打包后的预处理器）：**20/20 通过**
- 消费者测试：`test_package/` 用打包后的 `amd64-linux-pcc` 真实编译一个自足翻译
  单元并断言生成的汇编含 x86-64 目标代码

## 参考资料

- [上游仓库](https://github.com/IanHarvey/pcc)
- [pcc 官方主页](http://pcc.ludd.ltu.se/)（已失效）

## conan

```bash
conan install --requires=pcc/1.2.0-devel-20220331 -r=ohpcd
```
