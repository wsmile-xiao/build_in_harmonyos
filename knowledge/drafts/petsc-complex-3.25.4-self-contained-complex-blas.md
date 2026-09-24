# petsc-complex 3.25.4：自带 f2cblaslapack 已含 z 例程，复数构建无需外部 BLAS；ABI 宏经 petscconf.h 传播

> Draft: DRAFT-PETSC-COMPLEX-3254-SELF-CONTAINED-COMPLEX-BLAS
> Stem: `petsc-complex-3.25.4-self-contained-complex-blas` — 与本名 `.kv` 成对

## 基本信息

- **ID**: DRAFT-PETSC-COMPLEX-3254-SELF-CONTAINED-COMPLEX-BLAS
- **严重度**: 2
- **类别**: conan-recipe-dependencies
- **触发工具**: configure|make|conan
- **阶段**: configuration|dependency-resolution|packaging

## 错误特征

最典型的误判是先把依赖加进去：

```python
def requirements(self):
    self.requires("openblas/0.3.x")   # 复数 Building 就该加个带 zgemm 的 BLAS？
```

以及反向的过度补救：

```python
self.cpp_info.defines = ["PETSC_USE_COMPLEX"]   # 以为必须由配方 -D 告知消费方 ABI
```

两者都不是必需的。

## 根因分析

### 1）复数 BLAS 的直觉是错的

从实数切到复数时，直觉会认为"现在需要带 `zgemm`/`zdotc`/`zheev` 的 BLAS/LAPACK"，
而这类例程通常来自 OpenBLAS 或 MKL —— 那就会把尚未发布到制品仓的依赖拖进 OHOS 图。

实际上 PETSc 的 `--download-f2cblaslapack=1` 抓取的 `f2cblaslapack-3.8.0.q2`
是 netlib 的 f2c 移植版，**同时包含实数和复数例程**：

```
blas/zgemm.c     blas/zdotc.c     lapack/zheev.c
```

所以复数变体与实数变体一样自包含。

> 注意：这是**必须验证**的前提，不是可以假定的。解包比对后再下结论，否则
> "自包含"可能只是运气好没编到那个例程。

### 2）ABI 宏已经由头文件承载

`petscconf.h` 是 PETSc configure 生成的，`PETSC_USE_COMPLEX` 被写进去；
`petscsys.h` 会 `#include <petscconf.h>`，而 `petsc.h` 会拉进 `petscsys.h`。
因此任何对着**安装出来的头文件**编译的消费方，自动拿到正确的变体 ABI ——
不需要配方额外 `-D`。

推论（很容易踩）：`package()` 必须走 PETSc 自己的 `make install`，
不能手工 `copy` 一个 `include/` 目录。手工拷贝会漏掉生成的 `petscconf.h`，
消费方就同时丢掉宏和配置值。

配方里保留 `defines` 只是为了生成自描述的 CMake/pkg-config 文件；
**头文件才是真相源**。

## 解决方案

**主方案**: reuse-bundled-f2cblaslapack-plus-header-borne-abi-macro

沿用实数同族的自包含 configure，只加两项变体开关：

```
--with-fc=0
--with-mpi=0
--download-f2cblaslapack=1
--with-scalar-type=complex      # 新增
--with-precision=double         # 新增（显式写出默认值）
```

`requires()` 为空，依赖图里没有 BLAS/LAPACK provider。
`package_info()` 保持：

```python
self.cpp_info.libs = ["petsc", "f2clapack", "f2cblas"]
self.cpp_info.includedirs = ["include", os.path.join("include", "petsc")]
self.cpp_info.defines = ["PETSC_USE_REAL_DOUBLE", "PETSC_USE_COMPLEX"]
if self.settings.os in ("Linux", "OHOS"):
    self.cpp_info.system_libs = ["m", "stdc++"]
```

`package_type = "library"`（库类型，不建 `commands.json`）。

## 适用范围

- 仓库内所有 PETSc 配方（`petsc` / `petsc-complex` 家族）；
- 广义上：**任何提供 bundled BLAS/LAPACK 回退的项目**，在因为标量变体去加外部
  provider 之前，先确认 bundled 版本是否已经覆盖该变体；
- "生成式配置头被总头文件传递包含"这一点适用于任何这类项目
  （保证 ABI 宏传播、并决定 package() 必须走 upstream install）。

## 验证

```sh
# 前提验证：bundled 镜像确实含复数例程
tar -tzf f2cblaslapack-3.8.0.q2.tar.gz | grep -E 'blas/zgemm\.c|blas/zdotc\.c|lapack/zheev\.c'
# → blas/zgemm.c  blas/zdotc.c  lapack/zheev.c

conan create archives/p/petsc-complex/3.25.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr
# test_package: assertions: 11, failures: 0（含 GMRES 复数求解端到端）
```

## 关联条目

- 同族：`petsc/3.25.3`（self-contained serial PETSc：`--with-mpi=0` + 
  f2cblaslapack，未涉及复数）
- 配套条目：`petsc-complex-3.25.4-abi-variant-separate-conan-package`
  （为什么变体要独立成包 + 变体测试怎么写）
