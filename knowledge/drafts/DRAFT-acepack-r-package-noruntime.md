# DRAFT: R 包（r-cran-*）在 OHOS 缺 R 运行时 + gfortran 无法编译

- **id**: `DRAFT-acepack-r-package-noruntime`
- **来源**: acepack/1.6.3 适配尝试（W0 依赖检查 / init-build / Step2 编译）
- **状态**: 草稿（未提升为正式 E 条目）

## 错误特征

```
R CMD INSTALL: R: inaccessible or not found
sh: R: inaccessible or not found
gfortran: No such file or directory
configure: No such file or directory
No targets specified and no makefile found
```

## 根因

acepack 1.6.3 是 GNU R 包（r-cran-acepack, `NeedsCompilation: yes`）：
- `src/` 为 Fortran 90（`*.f90`）+ C（`init.c`），由 **R 构建系统（`R CMD INSTALL`）** 驱动
- 顶层**无 configure / Makefile** → 不适用于 autotools 流程
- **【深度查询修正 2026-08-05】真正硬阻塞 = R 运行时（r-base）未发布**：
  - 制品仓 ohpcd 0 个 `r/*` recipe，`conan download r-base` 无匹配，resolve-deps 1248 包与 archives/ 均无 R 运行时 → R36 依赖链断裂，必须先发布 r-base
  - Fortran 编译器缺失**可解**：制品仓已有 `flang-ohos/20.1.0`（arch=armv8, os=OHOS 6.0 binary），参考 E242 与 libxc 7.1.2 模式（`tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")`），openblas/mpich/octave/tfel 等 8 个 Fortran 库已 built 佐证（E109 rec=use-prebuilt-package）

构建链路 = R 运行时 → src/Makevars → flang-ohos 编译 .f90 → 链接 .so → 安装到 R 库目录。

## 推荐方案

1. 先适配并发布 **R 运行时（r-base）** 到制品仓（R36 依赖优先）
2. Fortran 用 `flang-ohos/20.1.0` 预编译包（E242/libxc 7.1.2 模式），无需等 gfortran
3. 若仅需 ACE/AVAS 算法能力，可用纯 C/C++ 等价库（LAPACK/Eigen）替代
4. 当前标记 failed，等 r-base 就绪后重试

## 关联

- 相似条目：E109（Fortran 编译器缺失）
- 验证命令：`which R Rscript gfortran; R CMD INSTALL .`
