# rapmap

## 简介
RapMap 是转录组短序列比对器，用 quasi-mapping 把 RNA-seq reads 定位到转录本集合上，
是 salmon 定量流程中负责建索引与比对的那一层。本包提供 `rapmap` 命令行工具，
含两个子命令：`quasiindex`（建准索引）与 `quasimap`（比对并输出 SAM）。

## 功能概述
- `rapmap quasiindex -t transcripts.fa -i <index>`：构建准索引，支持 `--perfectHash`
- `rapmap quasimap -i <index> -1 r1.fastq -2 r2.fastq -o out.sam`：paired-end 比对
- `rapmap quasimap -i <index> -r single.fastq`：single-end 比对
- `--bamOut` 经随包的 `RunRapMap.sh` 调 `samtools` 转 BAM（运行期需要外部 samtools）
- `rapmap --version` / `--help`

## OHOS 适配
构建系统为 CMake，配方用 CMakeToolchain/CMakeDeps，交叉目标 aarch64-linux-ohos。

**依赖：全部改为消费制品仓包，构建期零联网。**
上游 `CMakeLists.txt` 里有 3 处 `ExternalProject_Add`：

| 依赖 | 上游做法 | 本适配 |
|---|---|---|
| libdivsufsort | 包内 tarball + 嵌套 CMake 自建（不继承交叉工具链，强制 OpenMP） | `find_package(libdivsufsort)`，走 `divsufsort::divsufsort` / `divsufsort64::divsufsort64` |
| cereal 1.2.2 | `curl -k -L` 联网拉取后手工拷头文件（仅 `if (NOT CEREAL_FOUND)` 时） | `find_package(cereal)` + 链接 `cereal::cereal` |
| jemalloc 4.5.0（fork） | `curl -k -L` 拉取后跑 `autogen.sh`（仅 `if (NOT HAVE_FAST_MALLOC)` 时） | `find_package(Jemalloc)` 命中制品包；兜底分支改成 configure 期 FATAL_ERROR，杜绝静默联网 |

**aarch64 移植点（三个补丁）：**
1. `0001` 顶层 CMakeLists 消费上述 Conan 包、删除三处下载步骤。
2. `0002` `src/CMakeLists.txt` 用 imported target 取后缀数组库与 cereal 头，
   删掉指向上游 `external/install` 的硬编码路径与失效的 `add_dependencies(rapmap libjemalloc)`；
   非 x86 架构不再创建 `ksw2pp_sse2` / `ksw2pp_sse4` 两个 OBJECT 库。
3. `0003` `src/ksw2pp/KSW2Aligner.cpp`：x86 `cpuid` 内联汇编的 SIMD 探测按 `__i386__/__x86_64__`
   编译，其它架构报告"无 SIMD"（`haveSSE2/haveSSE41` 保持默认 false）；
   `ksw_extz2_sse2/sse41` 与 `ksw_gg2_sse` 调用点用 `__SSE2__` 包住，
   非 SSE2 走标量 `ksw_extz` / `ksw_gg2`。
4. `0004` `scripts/RunRapMap.sh`（上游 `install(FILES ...)` 进 `bin/`）的 shebang
   由写死的 `/bin/bash` 改为 `/usr/bin/env bash`：HarmonyOS PC 上没有
   `/bin/bash` 与 `/usr/bin/bash`（实测 `[ -e ]` 双双不成立，而 `/usr/bin/env` 与
   `/data/service/hnp/bin/bash` 存在），内核按字面路径解析 shebang，
   因此该 helper 装完必然 ENOENT，**且与 PATH 无关**。改后实测可执行。

关键判断：上游 ksw2 的每个 SIMD 内核函数体都整体包在 `#ifdef __SSE2__` 里，
所以 aarch64 上它们不是"编译不过"，而是"编成空目标文件"——真正的断点是链接期
`KSW2Aligner.cpp`（被 `RapMapSAMapper.cpp` 使用）仍引用这些不存在的符号。
替代用的标量内核正是上游自己在非 SIMD 分支里已经在调用的那一个：
`ksw_gg2` 与 `ksw_gg2_sse` 形参表完全一致（含 CIGAR 三个出参），
`ksw_extz` 与 `ksw_extz2_sse*` 差一个 `end_bonus`，而上游 else 分支的替换就是丢掉它。
因此本适配未新造算法语义，只把上游已有的降级路径按架构接上。

另：OHOS clang 15 对 aarch64 传 `-msse2` / `-msse4.1` 只报
`-Wunused-command-line-argument` 警告且 RC=0，故不必为标志本身改动编译选项。

上游无条件追加 `-march=native` ⇒ 配方打开上游自带的 `NO_NATIVE_ARCH` 开关，
避免产物把指令集钉在构建机上。

**未改动**：上游内部版本串硬编码 `0.6.0`（`include/RapMapConfig.hpp:31`），
`rapmap --version` 输出 `rapmap 0.6.0` 而非 tag 版本 `0.15.0`。这是上游 tag 版本与其
内部串的既有偏差，patch 它会牵连索引头版本字段，故保留原样并在此说明。

## 测试
- 上游 CTest 2 例：`quasi_map_test`、`quasi_map_test_ph`
  （`cmake/TestQuasiMap*.cmake`：对包内 `sample_data/` 的 transcripts.fasta +
  reads_1/2.fastq 跑 quasiindex → quasimap，断言产出 .sam），
  **不需要联网**，在配方 `build()` 内执行。
- test_package 用 `test.sh` 从消费者视角跑打包后的 `bin/rapmap`：
  断言 `--version`、`--help` 子命令说明，再造一份小转录本 + reads 走完整
  quasiindex/quasimap 闭环并校验 SAM 输出行数与比对记录。
- 实测数字见版本目录 `notes.md` §7，申报值以运行日志为准。

## 依赖关系
- 构建/运行依赖：`zlib/1.3.1`、`cereal/1.3.2`、`libdivsufsort/2.0.1`、`jemalloc/5.3.0`
  （以上均已在制品仓发布，二进制可用性经 OHOS profile + `--build=never` 实测）
- 运行期：`libc++`（OHOS 系统）、系统线程库

## 参考资料
- 上游仓库：https://github.com/COMBINE-lab/RapMap
- 本包对应 tag：`salmon-v0.15.0`（commit `de73d6841932`）
- 论文：Srivastava A et al., "RapMap: A fast and efficient open-source tool for
  pseudo-alignment and quantification", J. Open Source Softw. 2017
