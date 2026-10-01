# piler

[PILER](https://www.drive5.com/piler/)（Parsimonious Inference of a Library of
Elementary Repeats）是一个基因组重复序列分析工具，由 Robert C. Edgar 编写、
捐赠至公有领域。本仓提供其在 HarmonyOS PC（OHOS aarch64）上的适配。

## 简介

- **构建产物**：单一命令行工具 `bin/piler2`
- **语言 / 构建系统**：C++（约 40 个 TU）/ 手写 Makefile
- **依赖**：无第三方依赖（仅 libc / libm）
- **能力**：
  - `-trs` / `-trs2fasta`：散在重复（transposed repeat）家族识别与家族 FASTA 导出
  - `-crisp`：CRISPR 阵列检测
  - `-tr`：LTR 反转录转座子家族识别
  - `-tan` / `-tanmotif2fasta`：串联重复金字塔与 motif 导出
  - `-cons`：多序列比对一致性序列
  - `-annot` / `-annotedge`：第三方重复注释（RepeatMasker 风格）图示叠加

## OHOS 适配要点

上游 Makefile 面向通用 Linux 编写，在 OHOS aarch64 上需要三处最小修改
（见 `0-20140707/patches/0001-ohos-makefile-toolchain-hardening.patch`）：

1. `GPP = g++` → `GPP = $(CXX)`：OHOS 工具链只有 clang++，原样构建报
   `g++: No such file or directory`（make Error 127）。
2. `CFLAGS = ...` / `LDLIBS = -lm -static` → `CFLAGS += ...` /
   `LDLIBS = $(LDFLAGS) -lm -static-pie`：让工具链传入的标志生效。
3. `-static` → `-static-pie`：既保留上游"自包含单文件二进制"的语义
   （无 `DT_NEEDED`，不依赖设备上无保证的共享 libc++），又产出
   PIE + full RELRO + NX，满足鸿蒙硬化基线（conan-verify L4）。

## 使用

```bash
conan install --requires=piler/0-20140707
piler2 -version
piler2 -help
piler2 -crisp hits.gff -out crisp.gff
piler2 -trs hits.gff -out trs.gff -piles piles.gff -images images.gff
piler2 -trs2fasta trs.gff -seq genome.fasta -path fams -prefix dmel
piler2 -cons aln.fasta -out cons.fasta -label fam1
piler2 -annot in.gff -rep repeats.gff -out out.gff
```

## 上游测试状况

上游 tarball **不含任何自动化测试**（无 `tests/`、Makefile 无 `check`/`test`
目标、无 ctest/pytest、无样例数据）。本仓的功能覆盖由 `test_package/`
按上游 User Guide 记载的全部工作流补全（16 项）+ 2 项 OHOS 适配专项用例，
详见 `0-20140707/reports/test-report.md`。

## 参考

- 官网：<https://www.drive5.com/piler/>
- 用户手册：<https://www.drive5.com/piler/piler_userguide.html>
- 源码：<https://www.drive5.com/piler/piler_source.tar.gz>
- 引用：R.C. Edgar and E.W. Myers, *PILER: identification and classification of
  genomic repeats.* Bioinformatics. 2005 Jun 1;21 Suppl 1:i152-i158
