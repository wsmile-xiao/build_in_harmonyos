# boot 1.3-32 适配笔记

## 库概况
- **软件**：boot 1.3-32 = CRAN 的 R 包「Bootstrap Functions」（Davison & Hinkley
  1997, *Bootstrap Methods and Their Application*, CUP；最初由 Angelo Canty 为 S 编写）
  - 提供 `boot()`/`boot.ci()`/`censboot()`/`tsboot()`/`abc.ci()`/`saddle()` 等
    自助法（bootstrap）函数与 50 个配套数据集
- **License**：`Unlimited`（DESCRIPTION 显式声明；上游作者 Angelo Canty / Brian Ripley /
  Alessandra R. Brazzale，维护者 Alessandra R. Brazzale <brazzale@stat.unipd.it>）
- **类型**：**纯 R 语言包**，DESCRIPTION 声明 `NeedsCompilation: no` —— 无 C/Fortran
  源码，**没有任何编译步骤**
- **官方源**：https://cran.r-project.org/src/contrib/boot_1.3-32.tar.gz
  - sha256: 3a05aced6fea42a5c310c5c6ab7a2019f69f757f5e77c4961183977747136c97
  - size: 238282 bytes；tar_format: tar.gz；根目录 `boot/`（→ `strip_root=True`）

## 上游结构（实测统计）
| 组件 | 内容 | 数量 |
|------|------|------|
| 顶层文件 | ChangeLog / DESCRIPTION / INDEX / MD5 / NAMESPACE | 5 |
| `R/` | `bootfuns.q`（123227 B）+ `bootpracs.q`（10070 B） | 2 |
| `data/` | `*.rda`（全部 RDX2 格式，gzip 压缩） | **50** |
| `man/` | `*.Rd`（其中含 `\examples` 的 **25** 个） | **88** |
| `inst/` | `CITATION`、`bd.q`、`po/**`（8 个语言 `.mo`） | — |
| `po/` | `R-boot.pot` + 6 个 `R-*.po`（de/fr/it/ko/pl/ru） | 7 |
| `tests/` | `parallel-censboot.R`（1 个测试）+ `Examples/boot-Ex.Rout.save`（2008 行，`^> ` 输入表达式 **915** 条） | 2 |
| 合计 | 上游文件总数 | 163 |

- **NAMESPACE 实测**：`export(...)` **36 个**（abc.ci, boot, boot.array, boot.ci,
  censboot, control, corr, cum3, cv.glm, EEF.profile, EL.profile, empinf,
  envelope, exp.tilt, freq.array, glm.diag, glm.diag.plots, imp.moments, imp.prob,
  imp.quantile, imp.weights, inv.logit, jack.after.boot, k3.linear, lik.CI,
  linear.approx, logit, nested.corr, norm.ci, saddle, saddle.distn, simplex,
  smooth.f, tilt.boot, tsboot, var.linear）；`import(stats)`；
  `importFrom(graphics, abline, hist, identify, layout, lines, par, plot, text)`（8）；
  `S3method` **7 条**（c.boot, lines.saddle.distn, plot.boot, print.boot,
  print.bootci, print.saddle.distn, print.simplex —— 已注册但不在 export 名单）。
- **DESCRIPTION 关键字段**：Package: boot；Version: 1.3-32；Priority: recommended；
  License: Unlimited；NeedsCompilation: no；Depends: R (>= 3.0.0), graphics, stats；
  Suggests: MASS, survival；LazyData: yes；ByteCompile: yes；
  Date/Publication: 2025-08-29。

## 依赖决策（W0 实测证据）
- **r-base 未发布**：ohpcd 制品仓无 r-base。
  - `conan download r-base/4.5.1 -r=ohpcd --only-recipe` → **HTTP 404 / Recipe not found**；
  - 全量 **7802** 条配方搜索无任何 R 系包。
- **L0i 门禁 hard-fail**：CI 的 L0i（commit 83c2f54f25 起）对**未发布依赖** hard-fail
  —— 本地对 `archives/a/acepack/1.6.3`（历史 R 包配方，走 `R CMD INSTALL` +
  r-base 依赖）实测复现：`L0_RESULT=fail: gate failed:registry_unreachable`。
- **结论**：本配方**零 `requires` / 零 `tool_requires`**。boot 上游本就是纯 R、无编译，
  连「独立数值库」都不需要（对比同族先例 kernsmooth：那里有 Fortran 源码，才需要
  flang-ohos + openblas 走独立静态库路线）。boot 直接走「**R 包树数据搬运**」：
  build() 不编译，只做 R-free 自检；package() 把整棵 R 包树装进 `lib/R/library/boot/`。

## 适配点
- `package_type = "library"`；`settings = os/arch/compiler/build_type`（统一四项）。
- `validate()`：`os in ("Linux", "OHOS")`（**R32**，不用裸 `== "Linux"`）。
- `source()`：`get(strip_root=True)`；`sources` 中剔除 `tar_format` 元数据字段后再展开
  （`get()` 不认该关键字）。
- `build()`：**R-free 包树自检** —— 调用 `test_package/validate_boot.py` 校验源码树，
  打印 PASS 与 assertions 统计；失败抛 `ConanException`。这样 CI 日志中有真实测试
  痕迹（满足 L1b/L1c）。无编译，故不涉及 R33（无 shell 变量编译器）、R26（无系统同名库）。
- `package()`：`shutil` 递归搬运 `DESCRIPTION/NAMESPACE/INDEX/ChangeLog/MD5` +
  `R/data/man/inst/po/tests` 到 `lib/R/library/boot/`；并从 DESCRIPTION 抽取
  `License:`/`Author:`/`Maintainer:`/`Authors@R:` 写为 `licenses/LICENSE`（附来源说明）。
- `package_info()`：`runenv_info`/`buildenv_info` 定义 `R_BOOT_PACKAGE_DIR`；
  **不臆造 `cpp_info.libs`**（本包无库文件），`includedirs/libdirs/bindirs` 置空。
- 无补丁（纯 R，无平台相关源码）；`patches: {}`；库类包无需 `commands.json`（R38）。

## 测试策略（R34/R51）
- **CI 无 R 运行时**（ohpcd 无 r-base，无法 `tool_requires`）→ CI 侧为 R-free 的
  结构/数据校验，build() 与 test_package 两侧跑同一个 `validate_boot.py`（实测
  **229 项断言、0 失败**；`lib/` 被移走时失败，满足 CI L1e 破坏性反向验证）。
- **本地**（自建 R 运行时）由 `test_package/R/` 三脚本实测上游真实 R 测试
  （run_upstream_examples.R / run_upstream_tests.R / test_boot_api.R，另由协作者
  子任务编写）。
- 上游测试资产如实申报（见 `test_package/MANIFEST.yml`）：`upstream_test_in_build: false`
  —— CI 环境无 R，故上游 R 测试在 build() 中不执行，原因已写明。

## 验证方法
- `conan create archives/b/boot/1.3-32 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
  → build() 内跑 `validate_boot.py <source_folder>`（源码树形态）→ PASS；
  → test_package 内跑 `validate_boot.py <package_folder>`（安装形态）→ PASS；
  → `assertions=229 failures=0`，`BOOT_VALIDATE_PASS`，exit 0。
- 单独复跑校验器（无需 conan）：
  - 源码树：`python3 test_package/validate_boot.py <解压后的 boot/>`
  - 安装树：`python3 test_package/validate_boot.py <package_folder>`

## 注意事项
- `/tmp` 只读（E002）：校验器建临时目录时用 `tempfile`（尊重 `$TMPDIR`），
  构建环境须 `export TMPDIR=$HOME/tmp`。
- R 包 `.rda` 的 R-free 校验法：gzip 魔数 `1f 8b` + 解压后 5 字节属
  {`RDX2\n`,`RDX3\n`,`RDA2\n`,`RDA3\n`}；数据集**列名**以 R 序列化 CHARSXP 前缀
  （`00 00 04 09` + 4 字节长度 + 名字字节）在解压字节流中定位，可在无 R 环境精确核验。
- 版本号策略（R37）：首次适配用上游版本 `1.3-32`（无适配修复后缀）。
- R39：源码 URL 全部为官方 CRAN 站点 + 4 个权威镜像，无 fork/网盘/代理。
---

**编译结束**: 2026-10-10 10:48
**最终状态**: built
