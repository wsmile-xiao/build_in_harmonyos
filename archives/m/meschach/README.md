# meschach

Meschach 是 David E. Steward 与 Zbigniew Leyk 编写的 C 语言矩阵/向量计算库
（稠密与稀疏线性代数、分解、求解、最小二乘、特征值…），上游最后版本 1.2b
（1999-05-15 原始 tarball），无活跃上游仓库；Debian/Ubuntu 持续打包至 1.2b-19。

- 适配版本目录：`archives/m/meschach/1.2b/`（autotools，静态库，仅依赖系统 libm）
- 源码锚定：Ubuntu 池 orig tarball，sha256 与 deb.debian.org / qlu 镜像 / 官方 .dsc 三面全等
- 上游页面：https://maths.anu.edu.au/research/cma-proceedings/meschach-matrix-computations-c
- 知识沉淀：E704（complex.h 宏与内建 typedef 撞名的 configure 侧修法 + `--with-all`
  守卫宏对齐），草稿见 `knowledge/drafts/E704-draft-*`
