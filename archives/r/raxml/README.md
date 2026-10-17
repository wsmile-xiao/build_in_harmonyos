# RAxML (standard-RAxML)

RAxML (Randomized Axelerated Maximum Likelihood) is a program for
sequential and parallel Maximum Likelihood based inference of large
phylogenetic trees. This archive provides the standard RAxML version
8.2.13 CLI (`raxmlHPC`) adapted for HarmonyOS PC (aarch64).

## 版本

- 8.2.13 — built (2026-09-28)

## 构建

纯 Makefile 构建（无 configure / 无 install 目标）：

```bash
make -f Makefile.gcc CC=clang -j1
```

产物为 `raxmlHPC`（`bin/`）。

## 适配要点

- Makefile.gcc 已内置 aarch64 分支（`ARCH_CFLAGS=` 为空），源码自带
  `sse2neon.h`，无需额外 SIMD 适配。
- 上游 v8.2.13 tag 内版本横幅仍为 8.2.12（上游版本字符串未同步）。
- 上游无测试资产；test_package 提供自研消费者测试（版本横幅 +
  最小 PHYLIP 数据 GTRCAT 最大似然搜索生成结果树）。
