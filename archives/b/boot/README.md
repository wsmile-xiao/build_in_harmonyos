# boot

`boot` 是 CRAN 的 R 包「Bootstrap Functions」（Davison & Hinkley 1997,
*Bootstrap Methods and Their Application*, Cambridge University Press），
提供自助法（bootstrap）函数与配套数据集。

- 上游：CRAN R 包 boot（https://cran.r-project.org/package=boot）
- 版本：1.3-32（Date/Publication: 2025-08-29）
- 许可：`Unlimited`（DESCRIPTION 声明）
- 类型：**纯 R 语言包**（`NeedsCompilation: no`，无 C/Fortran 编译）

## 功能概述

- 通用自助法：`boot()`、`boot.ci()`（多种置信区间）、`boot.array()`
- 特殊场景自助法：`censboot()`（删失数据）、`tsboot()`（时间序列）、
  `tilt.boot()`（重要性/指数倾斜）、`abc.ci()`（近似贝叶斯）
- 影响函数与诊断：`empinf()`、`linear.approx()`、`jack.after.boot()`、
  `glm.diag()`、`glm.diag.plots()`、`imp.weights()`、`saddle()`、`saddle.distn()`
- 通用工具：`control`、`corr`、`cum3`、`inv.logit`、`logit`、`simplex`、`smooth.f`
- 数据集：50 个（`aml`、`aids`、`cloth`、`nuclear`、`melanoma`、`survival` 等）
- 文档：88 个 man 页（其中 25 个含 examples）

## OHOS 适配

- **纯 R 包，无编译**：上游没有 C/Fortran 源码，本仓不做任何编译，只把上游整棵
  R 包树（`DESCRIPTION`/`NAMESPACE`/`R`/`data`/`man`/`inst`/`po`/`tests`/`INDEX`/
  `ChangeLog`）原样安装到 `lib/R/library/boot/`，供下游 R 运行时 `library(boot)` 加载。
- **零未发布依赖**：ohpcd 制品仓**没有 r-base**（实测 HTTP 404，全量 7802 条配方
  无任何 R 系包），且 CI 的 L0i 门禁对未发布依赖 hard-fail。因此本配方**不声明任何
  `requires` / `tool_requires`**（同族先例 kernsmooth 亦绕开 r-base 走独立路线）。
- **CI 无 R 运行时**：CI 侧做 R-free 的结构/数据校验（`test_package/validate_boot.py`，
  229 项断言）；上游真实 R 测试在 CI 不执行（原因见 `1.3-32/test_package/MANIFEST.yml`），
  由本地自建 R 运行时实测。
- **已知差异**：CI 门禁环境不提供 R，无法执行 `R CMD check` 与 `tests/*.R`；
  这是环境限制而非适配缺口，已如实申报。

## 依赖关系

- 编译依赖：**无**（零 requires / 零 tool_requires）
- 运行时依赖（R 侧，由消费方 R 环境提供）：`R (>= 3.0.0)`、`graphics`、`stats`
  （上游 `Depends`）；`Suggests`：`MASS`、`survival`
- 包内导出环境变量：`R_BOOT_PACKAGE_DIR` = `<package_folder>/lib/R/library/boot`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.3-32 | built | 纯 R 包树适配（零依赖、R-free 校验），见 `1.3-32/` |

## 参考资料

- CRAN 包页：https://cran.r-project.org/package=boot
- 源码：https://cran.r-project.org/src/contrib/boot_1.3-32.tar.gz
- 书籍：Davison, A.C. and Hinkley, D.V. (1997) *Bootstrap Methods and Their
  Application*. Cambridge University Press.
