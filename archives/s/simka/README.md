# simka

simka 是 GATB / Genscale 团队（INRIA）开发的 **k-mer 计数与多样本比较工具**：把测序
reads 切成 k-mer，按 minimizer 分区后并行计数，输出每个样本的 k-mer 丰度表、样本间
距离矩阵（Jaccard / Bray-Curtis / chord / hellinger 等 20 种），并附带一条基于
minhash 草图的近似流水线 simkaMin。它是基因组学流程里的常用统计前端，**不是**被
下游链接的库。

## 功能概述

- `simka`：主程序。对 `-in` 指向的元数据文件（样本 → fasta/fastq，支持双端）做
  k-mer 计数，产出丰度表与 21 个距离矩阵（其中 20 个可与上游 truth 逐字节比对）；`-simple-dist` / `-complex-dist` 额外产出
  丰度直方图；`-nb-cores` / `-max-memory` 控制分区并行与内存上限。
- `simkaCount` / `simkaMerge` / `simkaCountProcess`：计数与归并的分步入口（分区计数 →
  归并 → 供 potara 分布式后端调用的进程封装）。
- `simkaMinCore`：simkaMin 草图流水线的 C++ 后端，由 `simkaMin/` 与 `scripts/` 下的
  Python 脚本驱动。
- 安装布局沿用上游 `INSTALL` 指令：`bin/`（5 个可执行文件）+ `example/`（示例数据集）
  + `simkaMin/`、`scripts/*.py|r`（草图流水线）+ `README.md`、`LICENSE`。

## 依赖

| 层次 | 内容 |
|------|------|
| Conan 依赖（显式声明） | `zlib/1.3.2`（gatb-core 链接行写死 `z`，另有 5 个源文件 `#include <zlib.h>`） |
| 构建期 vendored 源码 | `thirdparty/gatb-core`（simka 的 git 子模块，官方 tag 归档不含其内容 ⇒ conandata 双源按锁定的 commit 补齐） |
| gatb-core 内嵌第三方 | `hdf5`（作为 CMake 子项目静态构建）、`boost`（header-only 子集）、`BooPHF`、`json` |
| 工具链 | clang 15（`aarch64-unknown-linux-ohos`）、CMake 4.x、Ninja |

除上表已列 Conan 依赖（zlib/1.3.2）外，无其他未适配缺口。

## OHOS 适配

1. **形态判定**：产物只有可执行文件 ⇒ `package_type = "application"`，并按 R38/PF8
   提供软件级 `commands.json`；`package_info()` 只声明 `bindirs`，不声明 `libs`。
2. **子模块补齐**：GitHub 的 tag 归档把 `thirdparty/gatb-core/` 打成空目录，直接
   configure 会在 `include(GatbCore)` 处 `FATAL_ERROR`。配方用两个官方不可变归档
   （simka tag 归档 + gatb-core 锁定 commit 归档，后者 `destination` 指到子模块路径）。
3. **CMake 4 策略下限**：上游顶层是 `cmake_minimum_required(VERSION 2.6)`，CMake 4.x
   已移除 <3.5 兼容 ⇒ 必须用 `cache_variables` 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
   （`tc.variables` 写进 toolchain 文件、在 `cmake_minimum_required()` 之后才加载，无效）。
4. **SIMD 分支**：gatb-core 在 Linux 分支上 `cat /proc/cpuinfo` 探 `sse2`/`sse4_2`
   决定是否加 `-msse2 -msse4.2 -mpopcnt`。aarch64 OHOS 实测两个探针都为假，
   x86 标志不会被注入（实测读数见版本级 notes.md）。
5. **zlib / HDF5**：内嵌 HDF5 的 zlib filter 显式置 `OFF`（它的 `find_package(ZLIB)`
   只认自家 tgz 布局），zlib 符号统一由 Conan 依赖提供，并把该包的 `lib/` 通过
   `-L` 喂给上游写死的 `-lz`，避免落回 sysroot 的系统 `libz.so`（R26）。
6. **全静态**：`BUILD_SHARED_LIBS=OFF`；产物包内不出 `.so`。
7. **测试口径**：上游 **0 个** `add_test`/ctest（且显式 `GATB_CORE_EXCLUDE_TESTS=1`），
   真正的上游测试是 `tests/simple_test.py`（4 个 k/丰度组合 × 20 个距离矩阵比对 +
   1 个并行不变性用例）与 `tests/simkaMin/test_simkaMin.py`（32 组参数组合，需
   python2 风格的 `python` 解释器）。消费者测试改为直接跑包内 `bin/simka` 并把
   产出的距离矩阵与上游 `tests/truth/` 期望值逐字节比对。明细见版本级 notes.md。

## 已知问题

- 上游 `tests/simple_test.py`、`tests/simkaMin/test_simkaMin.py` 硬编码
  `../build/bin/...` 相对路径，不能原样搬进 Conan 构建目录；本包用"复刻目录布局"
  的办法实跑取证据，功能断言在 `test_package` 里以确定性方式重做。
- 源码 URL 走 GitHub。CI 会把 GitHub 源改写进镜像且不校验状态码，存在"本地绿而
  CI 拿到的字节不符"的风险（详见版本级 notes.md 的披露段）。

## 参考资料

- 上游仓库：<https://github.com/GATB/simka>（tag `v1.5.3`）
- 内嵌核心：<https://github.com/GATB/gatb-core>（子模块锁定的 commit）
- 文献：Rahman M.A., Holley J., Medvedev P. (2019) *Simka: fast and flexible k-mer
  counting based on minimizer-partitioning.* Bioinformatics 35(6):1032–1034.
- 本仓版本级记录：`archives/s/simka/1.5.3/notes.md`
