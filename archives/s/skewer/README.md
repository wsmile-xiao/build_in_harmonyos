# skewer

`skewer` 是一个用于高通量测序（NGS）reads 的**适配子修剪 + 质量过滤**命令行工具，
实现 bit-masked k-difference matching 算法，专为 paired-end 数据设计，同时支持
single-end 与 long mate pair（LMP），并带多进程（`-t`）、barcode 拆分、
phred 质量修剪与压缩输入/输出能力。

上游 [relipmoc/skewer](https://github.com/relipmoc/skewer)（自 SourceForge
`skewer` 项目迁移而来，MIT 许可证；论文：Jiang et al., *BMC Bioinformatics*
15:182, 2014）。发布 tag 为裸版本号 `0.2.2`（无 `v` 前缀）。

## 功能概述

- 检测并去除 3' 端 Illumina 适配子（`-x`/`-y`，允许插入/缺失的近似匹配）
- 基于 phred 质量值的窗口化质量修剪（`-Q`/`-q`/`-p`），最短保留长度 `-l`
- 单端 / 双端 / LMP 三种输入模式，barcode 解复用（`-b`/`-j`）
- 多线程（`-t`）、gzip 压缩输入输出（`-z`）、输出 FASTQ/SAM 风格标签
- 产物：单个静态链接选项之外的原生可执行文件 `skewer`（本包为 `application`）

## 依赖关系

- 编译依赖：仅需 C++11 级编译器与标准库；`Makefile` 链 `-pthread` 与 `-lrt`
  （OHOS 侧由 musl libc / SDK sysroot 提供），**无任何第三方库**
- 运行依赖：无（纯文件/stdin I/O 工具，不需要终端图形能力）

## OHOS 适配要点

- 上游只有一个裸 `Makefile`（无 configure/CMake/autotools），且 `CXX=g++`
  写死在首行；OHOS 工具链只有 clang/clang++、没有 `g++` 别名，因此配方按 R33
  从 conan conf 取编译器路径后用 **`make CXX=<clang++> -j1`** 命令行覆盖接管，
  零源码补丁
- `CXXFLAGS?=-c` 里的 `-c` 是编译规则的命脉（链接规则不用 CXXFLAGS），配方
  **刻意不覆盖 CXXFLAGS**；实测覆盖成 `-O2` 会让每条"编译"变成链接并报
  `ld.lld: error: undefined symbol`
- 上游 `install` 目标是 `mv -f skewer /usr/local/bin`（绝对路径写死、无
  PREFIX/DESTDIR 支持、且把产物搬离构建树），因此 `package()` 不跑
  `make install`，自己 copy 到包内 `bin/`，产物内不留宿主绝对路径
- 上游无任何测试套件（无 tests 目录、无 `check` 目标、无测试源文件），
  消费者侧由 `test_package/test_skewer.sh` 提供 9 条鸿蒙断言（版本/用法/
  参数诊断 + ELF 架构/musl 解释器/NEEDED 集合/OHOS `.codesign` 标记与
  RPATH 检查 + 真实 FASTQ 适配子剪切功能断言）

版本细节见 [`0.2.2/notes.md`](0.2.2/notes.md)。
