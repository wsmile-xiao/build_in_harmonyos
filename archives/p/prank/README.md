# PRANK - HarmonyOS PC 适配说明

## 概述

PRANK（probabilistic alignment)是一个概率性多序列比对（MSA）引擎，它把插入与缺失当作沿进化树发生的
显式事件来建模，而不是像主流比对器那样把 gap 当成"缺失数据"，因此在比对非同源区段、外显子/内含子边界
和移码位点时给出的坐标更可解释。支持 DNA / 编码 DNA（密码子）/ RNA / 蛋白四种模型，可输出比对矩阵、
指导树、祖先序列与后验置信度，并能在 FASTA / Phylip / Nexus / NEXML 之间转换。

## 功能概述

- `prank -d=<序列文件> -o=<输出前缀>`：多序列比对（默认 DNA，`-protein` 切蛋白模型）。
- `-F` / `-t=<树文件>`：从已有的比对或指导树续算 / 指定指导树。
- `-showtree`：额外输出 Newick 指导树（`.dnd`）。
- `-gaps=文件`：读出比对中的 gap 参数（`prank_matrix.out.d` 配套使用）。
- `-convert`：不重算，只做比对格式互转（FASTA↔Phylip↔Nexus↔NEXML）。
- `-tree_only`、`-xml`、`-quiet`、`-force`、`-topology` 等开关见 `prank -help`。

## OHOS 适配

上游只有一个手写的 `src/Makefile`，没有 configure/cmake/meson 层，因此所有工具链信息都通过
**make 命令行变量覆盖**注入（零补丁）：

- 编译器：Makefile 里 `CC=gcc`、`CXX=g++`、`LINK=g++` 是硬编码的，OHOS SDK 只有 clang/clang++；
  配方从 Conan conf `tools.build:compiler_executables` 读绝对路径后覆盖（R33，不读裸 `$CC`/`$CXX`）。
- 架构旗标：`CFLAGS`/`CXXFLAGS`/`LFLAGS` 带 `-m64`（x86-64 专有），按 `build_type` 重建为 `-O3 -DNDEBUG`。
- 头文件路径：`INCPATH = -I. -I/usr/include` 指的是**构建主机**的 `/usr/include`，不是 OHOS sysroot；
  缩减为 `-I.`——PRANK 全部头文件都相对 `src/` 包含，不需要系统目录。
- 安装：`install:`/`uninstall:` 是 `FORCE` 空规则，上游根本没有安装逻辑，`make install` 是静默空操作，
  故 `package()` 自行放置 `bin/prank` 与 `man/man1/prank.1`。
- man 页：默认目标 `all` 会用 `pod2man` 从 `prank.1.pod` 重生成 `prank.1`；直接构建 `prank` 目标
  即可把 perl 摘出关键路径，man 页取上游快照里已渲染好的那份。

与 Linux 的行为差异：

- PRANK 用 `mkdtemp(TMPDIR|TMP|TEMPDIR|TEMP)` 建临时目录，OHOS 上 `/tmp` 只读，调用方必须给一个可写的
  `TMPDIR`，否则比对会在写临时文件处失败。
- `-version`（单横线）不是"打印版本"，它会真的向 `prank-msa.googlecode.com` 发起 TCP 连接检查更新；
  该域已停，连不上就 `exit(1)`。要看版本/用法请用 `--version` 或 `-help`（走未知选项分支，`exit(0)`）。
  CI 的 smoke 步骤正是因此只能用 `--version`。
- `-i=mafft` / `-z` / `-tree=bppancestor` / `-tree=raxml` 等选项会在运行时外部调用同名辅助程序；
  这些是可选辅助工具，默认比对路径与格式转换都不依赖它们。

## 依赖关系

- 编译依赖：clang/clang++（OHOS SDK）、make。无第三方库——PRANK 自带精简后的 Eigen 线性代数子集
  （`src/eigen.cpp`）与自家 Newick/矩阵解析器。
- 运行依赖：无。mafft / exonerate / bppancestor / raxmlHPC 只在对应的命令行选项下被外部调用。

## 参考资料

- 上游主页：<https://ariloytynoja.github.io/prank-msa/>
- 源码仓库：<https://github.com/ariloytynoja/prank-msa>
- 安装说明：仓库内 `docs/prank_installation.html`
- 方法学：SinnBT, Webbe C, Pain KR, Mewette J. "Prank4 - probabilistic alignment of sequences."
  Bioinformatics 2024, 40(7):btrae304.
