# seq-gen

## 简介

Seq-Gen 是 Andrew Rambaut 与 Nicholas C. Grassly 开发的分子序列演化模拟器：
读入一棵带分支长度的系统发育树（Newick 格式），沿树按指定替换模型做蒙特卡洛
模拟，输出 DNA 或蛋白质比对，广泛用于系统发育方法学的模拟研究。

## 功能概述

- 核苷酸模型：HKY、F84、GTR、GENERAL；氨基酸模型：JTT、WAG、PAM、BLOSUM、
  MTREV、CPREV45、MTART、LG
- 速率异质性：gamma 分布（`-a`，可分密码子位置）、离散类别数（`-g`）、
  不变位点比例（`-i`）、密码子位置速率（`-c`）
- 输出格式：PHYLIP（`-op`）、relaxed PHYLIP（`-or`）、NEXUS（`-on`）、
  FASTA（`-of`；不带 `-o` 时默认也是 FASTA 写到 stdout），可分数据集写多文件
- 多数据集（`-n`）、多分区（`-p`）、祖先序列输出（`-wa`）、位点速率输出
  （`-wr`）、可复现的随机种子（`-z`）

## OHOS 适配

### 1.3.5（feat/seq-gen-1.3.5）

- 构建系统是 `source/` 下的手写 Makefile（无 configure / CMake / meson），
  只产出一个可执行文件，**没有 install 目标**，配方自行把 `seq-gen` 落到 `bin/`
- 上游 Makefile 硬编码 `CLINKER = cc` 与 `CFLAGS = -O3`：鸿蒙 worker 上的 `cc`
  不是 Conan 提供的编译器，因此配方在 make 命令行上覆盖 `CLINKER`/`CFLAGS`
  （R33：取值来自 `tools.build:compiler_executables`，不裸用 shell 变量）
- **v1.3.5 tarball 内提交了一个预编译的 Mach-O arm64 二进制 `source/seq-gen`**：
  配方在 make 前删除它。留着既可能被 make 当成"目标已最新"而跳过重新链接，
  也会把一个无法在鸿蒙上执行的外来 ABI 产物打进包
- 源码本身是可移植 ISO C（只用 stdio/stdlib/math/time/string/ctype/limits），
  无平台 ifdef、无 socket/线程/特权调用，因此**不需要任何源码补丁**
- 链接 `-lm`：OHOS SDK sysroot 只提供 88 字节的 `libm.a` 桩，musl 把 libm 折进
  `libc.so`，故产物 `DT_NEEDED` 只有 `libc.so`（glibc 形态会是 `libm.so.6`，
  在设备上无法加载）
- 上游无测试套件（`test/` 只有数据文件 `ZIKV_100.newick.trees`，Makefile 无
  `check`/`test` 目标），由 `test_package` 补全 29 项独立检查：功能 20 项
  （F1-F20）+ 鸿蒙特有 9 项（A1-A9，纯 Python 解析 ELF，交叉编译机上也能实跑）
- 命令行工具，已按 R38 声明 `commands.json`
- `-h` 退出码为 0，但上游不实现 GNU 风格的 `--version` / `--help`（两者都
  退出码 1 并打印用法），因此 CI L2 smoke test 会给出 warn（非阻塞）

## 依赖关系

- 编译依赖：无（仅需 C 编译器与 make）
- 运行时依赖：鸿蒙 musl `libc.so`（含 libm 符号），无第三方库

## 参考资料

- 上游仓库：<https://github.com/rambaut/Seq-Gen>
- 使用手册：仓库内 `manual.md` 与 <http://rambaut.github.io/Seq-Gen/manual>
