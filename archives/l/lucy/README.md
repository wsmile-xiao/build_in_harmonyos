# Lucy

Lucy 是 TIGR（The Institute for Genomic Research，现 J. Craig Venter Institute）开发的
**DNA 序列质量修剪与载体去除工具**，用于在序列装配前清理自动化测序仪产出的原始读段。

## 功能概述

Lucy 把原始读段处理为可直接进入装配流程的高质量数据，全部流程集成在一个独立程序中：

1. **质量评估与修剪** —— 基于 phred 质量值（`-error` / `-window` / `-bracket`）确定每条读段的
   可信区间；
2. **置信度修正（confidence reassurance）** —— 用二级（2nd / ABI）碱基判定文件比对，
   对质量偏低但可与 ABI 判定吻合的读段进行"挽救"；
3. **载体检测与修剪** —— 用载体序列 + 剪接位点文件（`-vector`）识别并裁掉载体片段，
   完全不匹配的读段整体丢弃；
4. **输出** —— 存活读段的多重 FASTA（序列 + 质量）以及逐条读段的剪裁坐标报告
   （CLR/CLB/CLN/CLZ/CLV 区间）。

Lucy 不访问也不依赖数据库：输入是 ASCII 文本，输出也是 ASCII 文本。上游另附一个
`zapping.awk`，供消费者按下游需要把坐标区间物化成实际截断后的 FASTA。

## OHOS 适配

- **构建系统**：上游是裸 Makefile（目标 `all` / `lucy` / `beep` / `clean`），既没有
  `configure` 也没有 `install`，所以二进制与 man page 由 Conan 配方落盘
  （`bin/lucy`、`share/man/man1/lucy.1`）。
- **编译器**：Makefile 里硬编码 `CC = cc`，而 OHOS sysroot 只提供 clang，
  因此配方从 Conan 配置项 `tools.build:compiler_executables` 的 `c` 键取编译器
  （本仓 OHOS 版 conan 未注册 `:c` 子键形式，故读整字典后再取键；R33：不读 shell 环境变量）。
- **线程**：上游 `LIBS = -lpthread`，在 OHOS musl libc 下正常链接；多线程与单线程
  输出的一致性由上游测试用例覆盖（`-x N`）。
- **补丁**：无。1.20 源码在 clang 15 下零修改编译通过（仅有 C89 风格的历史告警）。
- **测试**：上游没有 `make check`，官方测试流程写在 `README.FIRST` §Testing，
  已实现为 `check/upstream-regression.sh` 并在 `build()` 中执行。

### 已知平台差异（非缺陷）

`abi.c` 用 libc `random()` 来解析二级序列里的歧义碱基（N/B/R/Y…）。glibc 与 OHOS musl
的 `random()` 序列不同，因此黄金文件 `lucy.debug` 中**含歧义碱基**的读段会有少量
坐标差异。上游 `README.FIRST` FAQ #6 明确记录了这一点，并指出**不含歧义碱基的读段
在任何平台输出一致** —— 这也是本项目黄金文件比对所采用的判定不变式
（见 `1.20/check/golden-compare.py`）。

### 陷阱

lucy 的 `-debug` 默认输出文件名就是随包发布的黄金基准 `lucy.debug`。裸写 `-debug`
会覆盖基准文件，使之后的比对变成自比对。使用 `-debug <文件名>` 显式指定
（上游 README 用的就是 `-debug lucy.info`）。

## 依赖关系

无编译依赖、无运行依赖（仅 libc；多线程版本另需 pthread，已包含在 OHOS musl libc 中）。

## 参考资料

- 官网：<https://lucy.sourceforge.net>
- 论文：Hui-Hsien Chou, Michael Holmes, *DNA sequence quality trimming and vector removal*,
  Bioinformatics 17(12):1093–1104, 2001
- 源码分发：SourceForge 项目 `lucy` 文件区（`lucy 1.20/lucy1.20.tar.gz`）
