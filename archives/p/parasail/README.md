# parasail

parasail 是一个 SIMD 序列比对 C 库，用于全局（Needleman-Wunsch）、半全局
（semi-global）和局部（Smith-Waterman）成对序列比对，内置 SSE2/SSE4.1/AVX2/
AltiVec/NEON 多套指令集实现并带有运行期 CPU 分发（CPU dispatch）。

## 功能概述

- 全局、半全局、局部比对算法（nw/sg/sw 及带查询/数据库端起止位置的变体）
- striped / scan / diag 三类 SIMD 向量化实现
- 可选统计信息（匹配数、相似度、打分表、回溯轨迹、CIGAR）
- 16/32/64 位及饱和饱和度（sat）打分类型
- 常见置换矩阵（BLOSUM/PAM 家族）内置头文件，支持自定义矩阵与 PSSM
- 附带 CLI 工具：parasail_aligner（批量比对）、parasail_stats（结果统计）

## OHOS 适配要点

### 构建系统

上游 GitHub tag 归档只含 autotools 源模板（configure.ac + Makefile.am + m4/），
不含生成的 configure；配方在 build() 内以 `autoreconf -fi` 自举，automake/1.18
与 libtool/2.5.4 经 tool_requires 提供（CI worker PATH 无 automake/libtoolize）。

### SIMD 后端

aarch64 上 configure 通过 `<arm_neon.h>` 编译探针自动启用 NEON 后端
（NEON_CFLAGS 由 configure 探测决定，未手工注入 SIMD 旗标）；SSE2/SSE4.1/
AVX2/AltiVec 在该目标编译探针不通过而自动关闭。库内运行期分发按 CPU 能力选择
实现，通用入口（如 parasail_nw）与 NEON 专用入口（如
parasail_nw_striped_neon_128_16）均可用。

### 可选依赖

zlib 为可选依赖（仅影响 aligner 的 gz 压缩输入支持），按零运行期依赖口径以
`--without-zlib` 显式关闭；核心比对库与其测试不依赖 zlib。

## 依赖关系

### 编译依赖
- autoconf 家族（autoconf/autoheader，构建环境提供）
- automake/1.18、libtool/2.5.4（Conan tool_requires，仅构建期）

### 运行依赖
- 无（libc/libm 之外零依赖）

## 使用示例

```c
#include <parasail.h>
#include <parasail/matrices/blosum62.h>

parasail_result_t *result = parasail_nw(
    "asdf", 4, "asdf", 4, 10, 1, &parasail_blosum62);
/* result->score == 20 */
parasail_result_free(result);
```

## 参考资料

- 官方仓库：https://github.com/jeffdaily/parasail
- 引用文献：Daily, Jeff. (2016). Parasail: SIMD C library for global,
  semi-global, and local pairwise sequence alignments. BMC Bioinformatics
  17(1), 1-11. doi:10.1186/s12859-016-0930-z
