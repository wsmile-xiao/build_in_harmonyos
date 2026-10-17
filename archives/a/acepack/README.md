# acepack

acepack 是 R 语言回归变换工具包，提供 ACE（交替条件期望）与 AVAS（方差稳定化变换）两种非参数回归变换方法，用于在多元回归中选择最优变量变换。核心 API 为 `ace()` 和 `avas()`，内部由 17 个 Fortran 90 源文件和一个 C 文件实现。

## OHOS 适配要点

- 构建方式为 `R CMD INSTALL`（无 configure/autotools/CMake），依赖 `r-base/4.5.1` 提供 R 运行时与安装驱动。
- Fortran 编译链由 `flang-ohos/20.1.0` 提供。因 r-base 制品 Makeconf 中 `FC=false`（可重定位清理），recipe 通过 `R_MAKEVARS_SITE` 环境变量注入 site Makevars 文件（`FC`/`F77`/`FLIBS` 覆盖），该文件在 Makeconf 之后被 include，从而正确覆盖 `FC=false`。
- C 编译器、AR、RANLIB 从 Conan conf（`tools.build:compiler_executables`）获取，不硬编码绝对路径。
- 上游 `tests/testthat.R` 依赖 testthat（Suggests），testthat 未适配，上游测试按 H2 未运行。

## 依赖

- `r-base/4.5.1`（host）：R 运行时与 `R CMD INSTALL` 驱动
- `flang-ohos/20.1.0`（tool）：Fortran 编译器与运行时库

## CRAN 参考资料

- 包主页：<https://cran.r-project.org/package=acepack>
- 源码包：<https://cran.r-project.org/src/contrib/acepack_1.6.3.tar.gz>
- License：MIT + file LICENSE
