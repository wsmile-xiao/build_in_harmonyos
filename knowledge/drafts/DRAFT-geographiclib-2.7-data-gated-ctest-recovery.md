# DRAFT-geographiclib-2.7-data-gated-ctest-recovery

## 问题 (Problem)

无依赖库（如 geographiclib 2.7）的上游 CTest 数据门控工具测试（GeoidEval0、
MagneticField0-6、Gravity0-3 等 12 项）在默认 OHOS 环境中**未实例化**：
`tests/CMakeLists.txt` 用 `if (EXISTS ${_DATADIR}/<模型文件>)` 守卫包裹 add_test 注册，
数据包（egm96-5/wmm2010/emm2015/egm2008/grs80）与 `GEOGRAPHICLIB_DATA` 环境变量缺失时
ctest -N 注册数为 199/211，12 项测试从未注册，无法声明完整上游测试通过。

## 根因 (Root Cause)

测试注册依赖运行时数据目录：`if (EXISTS $ENV{VAR}/.../数据文件)` 守卫在配置期求值，
默认 OHOS 环境既无官方数据包、也无 `GEOGRAPHICLIB_DATA` 指向 → add_test 分支整体跳过，
测试目标不生成、不注册、不执行。这是**数据门控注册机制**（数据缺失→注册缺失），
区别于依赖缺失（配方级）与编译门控（宏/条件编译互斥）。

## 方案 (Solution)

1. **官方数据包可取得性双重核验**（首次判定 + 最终回报前各一次）：
   `curl -sIL https://downloads.sourceforge.net/project/geographiclib/<distrib>/<pkg>.tar.bz2`
   确认 HTTP 200，且解压后数据文件存在可读。
2. **下载 + 注入**：`curl -sL -o <pkg>.tar.bz2 <官方URL> && tar xjf <pkg>.tar.bz2`，
   设置 `GEOGRAPHICLIB_DATA=<数据目录>`（或 cmake `-DGEOGRAPHICLIB_DATA=...`）。
3. **重配置 + 重构建 + 全量运行**：`cmake -S . -B build -DGEOGRAPHICLIB_DATA=...` 后
   `ctest --output-on-failure`，验证注册数 199→211、211/211 通过。

## 验证 (Verification)

- 注册数可量化: ctest -N 199/211（未恢复）→ 211/211（恢复后）
- 全量通过: ctest --output-on-failure → 211/211 Passed, 0 failed（data-ctest-full.log）
- 12 项逐入口: GeoidEval0 / MagneticField0-6 / Gravity0-3 各入口命令、cwd、退出码 0、日志
- 双重核验: data-download.log（首次 HTTP 200）+ data-availability-check2.log（最终回报前复核）

## 适用边界 (Applicable Scope)

- 仅适用**无依赖库的离线地理/科学数据门控测试**（add_test 注册守卫依赖运行时数据目录、
  数据可从官方源获取、注入环境变量后测试目标重新注册）。
- **不适用（反例）**：①所有"数据文件缺失"问题不能泛化（库本身无法构建/无法验证除外）；
  ②官方源不可达或数据为商业/受限许可 → 恢复不可行，走"记录差异+test_package 兜底"；
  ③测试注册与数据无关（纯编译门控/条件宏互斥）→ 属互斥分支说明，非此类。
- 与 E292（Apache-Arrow 分层迁移）关系：共享"测试数据环境变量注入恢复可执行子集"机制层；
  本条目为轻量无依赖库的窄场景组合（官方数据包双重核验 + 注册数可量化恢复），
  供 E292 覆盖外的简单库直接复用。

## 源事件 (Source Event)

- geographiclib 2.7 R02（pc2-5, task geographiclib-2.7-r02-...）：官方 SourceForge 数据包
  双重核验 + GEOGRAPHICLIB_DATA 注入后 12 项数据门控测试全部注册并运行通过，
  ctest 199/211 → 211/211 = 100%（data-ctest-full.log、data-download.log、
  data-availability-check2.log、test-ledger-r02-geographiclib-2.7.md）。