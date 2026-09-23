# minimap

> 基于 minimizer 的长序列快速近似比对工具与库。

## 简介

minimap 用于在两组长序列之间（读段 vs 参考、基因组之间、长噪声读段之间）
快速找到近似匹配位置。默认面向约 2 kb、约 20% 差异的匹配，速度快但特异度较低。
该版本不输出 alignment，只给出近似匹配区间。

同一仓库还提供可复用的库（`libminimap.a` + `minimap.h`）。

## OHOS 适配要点

- 纯 C；编译期依赖 **zlib**（Conan `zlib/1.3.1`）与 `libm`；pthread 在 OHOS
  bionic 下随 libc 提供，无需显式链接。
- 产物：`bin/minimap`、`lib/libminimap.a`、`include/{minimap.h,bseq.h,kseq.h}`。
- 上游是 Makefile 工程；本仓库按源文件逐个编译并显式传入 zlib 的 include/lib。
- 命令行工具：软件级提供 `commands.json`（R38）。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| zlib | 1.3.1 | 读取 gzip 压缩的 FASTA/索引 |

## 功能验证

```sh
minimap -V                                  # -> 0.2-r123
minimap target.fa query.fa > out.mini       # 直接映射
minimap -d target.mmi target.fa             # 建索引
minimap -l target.mmi query.fa > out.mini   # 用索引映射
```

库用法（参考上游 `example.c`）：

```c
#include "minimap.h"
mm_idx_t *mi = mm_idx_build("target.fa", 4, 7, 1); /* w=4, k=7 */
```

## 参考

- [源码仓库](https://github.com/lh3/minimap)
- [上游 README](https://github.com/lh3/minimap/blob/master/README.md)
