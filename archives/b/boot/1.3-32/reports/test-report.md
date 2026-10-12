# boot 1.3-32 测试报告

> **项目**: boot 1.3-32（CRAN R 包 "Bootstrap Functions"）
> **测试日期**: 2026-10-10
> **测试环境**: HarmonyOS PC (aarch64-unknown-linux-ohos)；CI 侧 clang15 交叉编译（无 R 运行时）；
>   本地 R 侧自建 R 4.5.1（本地构建 r-base/4.5.1 制品，`Rscript (R) version 4.5.1 (2025-06-13)`）
> **测试类型**: 上游官方测试（R CMD check 等价入口）+ 鸿蒙适配补全测试

---

## 一、测试摘要

### 1.1 CI 侧（R-free，conan create 内自动执行）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总断言数（validate_boot.py） | 229 | 100% |
| 通过 (PASS) | 229 | 100% |
| 失败 (FAIL) | 0 | 0% |

**CI 侧断言通过率**: ✅ **100%**

### 1.2 本地 R 侧（自建 R 4.5.1 实测上游测试与补全测试）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游 man 页示例（25 页逐条表达式） | 234 | 100% |
| 上游 tests/parallel-censboot.R | 1 | 100% |
| 数据资产校验（50 个 .rda load + 文档交叉） | 100 | 100% |
| 鸿蒙适配补全测试（test_boot_api.R） | 195 | 100% |
| 失败 (FAIL) | 0 | 0% |

**本地 R 侧总通过率**: ✅ **100.00%（430/430）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — boot 是纯 R 语言包（`NeedsCompilation: no`，无 C/Fortran 源码），
包树安装完整；CI 侧 229 项 R-free 结构/数据断言全部通过；本地自建 R 运行时下，
上游 25 个 man 页的 234 条示例表达式、上游 `tests/parallel-censboot.R`、
50 个数据资产与 195 条补全 API 断言全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| ohpcd 制品仓无 r-base | CI 侧无法执行 `R CMD check` 与上游 R 测试脚本 | 🟡 |
| 上游 `lik.CI`/`EEF.profile` 自身缺陷 | 2 个导出函数在 1.3-32 上游即不可用（非 OHOS 引入） | 🟢 |
| 上游 `lines.saddle.distn.Rd` 示例非确定性 | `rexp(12)` 无 `set.seed`，依赖 RNG 状态 | 🟢 |

### 2.3 可用功能清单

```
✅ 通用自助法: boot() / boot.ci() / boot.array() / boot.return()
✅ 特殊场景: censboot()(含 parallel="multicore") / tsboot() / tilt.boot() / abc.ci()
✅ 影响函数与诊断: empinf() / linear.approx() / jack.after.boot() / envelope()
✅ GLM 诊断: cv.glm() / glm.diag() / glm.diag.plots()
✅ 重要性重采样: imp.moments() / imp.prob() / imp.quantile() / imp.weights()
✅ 鞍点近似: saddle() / saddle.distn()
✅ 工具函数: control / corr / cum3 / freq.array / inv.logit / logit / norm.ci /
             simplex / smooth.f / var.linear / k3.linear / exp.tilt / nested.corr
✅ 数据集: 50 个（aml / cloth / acme / aids / nuclear / melanoma / …）全部可 load
⚠️ lik.CI / EEF.profile: 上游 1.3-32 自身缺陷（见 2.4），非 OHOS 适配问题
```

### 2.4 已知限制（如实申报）

1. **CI 环境无 R 运行时**：ohpcd 制品仓无 r-base（实测 HTTP 404，全量 7802 条配方
   搜索无任何 R 系包），CI worker 无法 `tool_requires` 到 R 解释器，因此
   `R CMD check` 与上游 R 测试脚本**在 CI 不执行**。CI 侧改以 R-free 的
   `test_package/validate_boot.py`（229 项断言）验证包树完整性与数据资产正确性；
   上游真实 R 测试由本地自建 R 运行时实测（本报告 §三）。
2. **上游自身缺陷（1.3-32 既有，未纳入"必过"断言）**：
   - `lik.CI`：内部 `lm(y ~ x + x^2)` 中 `x^2` 被 R 公式语言解析为线性项
     （应为 `I(x^2)`），二次项系数为 NA → 置信区间端点恒为 NA；
   - `EEF.profile`：引用包内 `zero` 闭包 → 报 `invalid type (closure)`。
   两者在 CRAN 上游即存在，与 OHOS 适配无关，已在测试脚本中作 NOTE 记录。
3. **上游示例的非确定性**：`lines.saddle.distn.Rd` 用例 `expdata <- rexp(12)`
   未固定随机种子，不同 RNG 状态下 `saddle.distn` 会随机报
   `unable to find range`（实测 seed 7/123 失败、seed 1/2/3/42/100/2024/2026 通过）。
   示例运行器对每个 Rd 文件固定 `set.seed(1L)` 使其可复现——这是**测试脚本的
   复现性措施**，未修改上游任何示例代码，未修改上游任何测试文件。
4. **平台说明（本地 R 侧，非本包问题）**：OHOS R 运行时的 LAPACK 符号仅局部可见，
   依赖 LAPACK 的扩展包（Matrix/survival）`dlopen` 时报
   `Error relocating …: dgebal_: symbol not found`；本地测试用
   `LD_PRELOAD=$R_HOME/lib/libopenblas.so` 使符号全局可见后，`library(survival)`
   正常加载（该问题属 r-base 制品，已在该包归档的 E316/E317 知识条目覆盖）。

---

## 三、测试详情

### 3.1 CI 侧：R-free 包树校验（validate_boot.py，229 断言，0 失败）

| 校验组 | 内容 | 断言数 | 结果 |
|--------|------|--------|------|
| A. DESCRIPTION | Package/Version/NeedsCompilation=no/License=Unlimited/LazyData/ByteCompile + Depends 三项 | 9 | ✅ PASS |
| B. NAMESPACE | export 集合 == 36 个期望名、import(stats)、importFrom(graphics,…) 8 项、7 条 S3method | 5 | ✅ PASS |
| C. R 源码 | 36 个导出名均在 R/bootfuns.q 或 R/bootpracs.q 中有 `<name> <- function` 定义 | 38 | ✅ PASS |
| D. 数据资产 | 50 个 .rda：gzip 魔数 + 可解压 + RDX2/RDA2 序列化头（3×50）+ 12 个数据集列名抽查 | 162 | ✅ PASS |
| E. 文档 | man/ 下 88 个 .Rd、25 个含 examples | 3 | ✅ PASS |
| F. 上游测试资产 | parallel-censboot.R 存在且含 censboot + `parallel="multicore"`；boot-Ex.Rout.save 含 915 条 `^> ` 输入行 | 6 | ✅ PASS |
| G. 负向自检 | 不存在路径 / 删 NAMESPACE / 删 data/ 必须失败 | 3 | ✅ PASS |
| **合计** | | **229** | **0 失败** |

### 3.2 本地 R 侧：上游 man 页示例（25 页 / 234 条表达式）

| 页 | 表达式数 | 结果 | 页 | 表达式数 | 结果 |
|----|---------|------|----|---------|------|
| boot.Rd | 23 | ✅ | linear.approx.Rd | 21 | ✅ |
| censboot.Rd | 23 | ✅ | tsboot.Rd | 17 | ✅ |
| boot.ci.Rd | 14 | ✅ | boot.array.Rd | 5 | ✅ |
| Imp.Estimates.Rd | 12 | ✅ | control.Rd | 5 | ✅ |
| envelope.Rd | 12 | ✅ | abc.ci.Rd | 6 | ✅ |
| plot.boot.Rd | 12 | ✅ | exp.tilt.Rd | 6 | ✅ |
| cv.glm.Rd | 11 | ✅ | simplex.Rd | 6 | ✅ |
| lines.saddle.distn.Rd | 9 | ✅ | saddle.Rd | 7 | ✅ |
| empinf.Rd | 9 | ✅ | tilt.boot.Rd | 7 | ✅ |
| smooth.f.Rd | 9 | ✅ | glm.diag.plots.Rd | 4 | ✅ |
| norm.ci.Rd | 8 | ✅ | jack.after.boot.Rd | 3 | ✅ |
| saddle.distn.Rd | 1 | ✅ | k3.linear.Rd | 2 | ✅ |
| var.linear.Rd | 2 | ✅ | **合计** | **234** | **100%** |

> 全部绘图示例重定向到临时 pdf 设备（无 X11 依赖）；
> `\dontrun{}` 块按上游约定跳过。

### 3.3 本地 R 侧：上游测试脚本与数据资产

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 上游 parallel-censboot.R | `Rscript tests/parallel-censboot.R`（需 survival；`parallel="multicore", ncpus=2`） | ✅ PASS（输出 5×1 矩阵；OHOS fork/multicore 可用） |
| 50 个 .rda 可 load | `load()` 逐个数据集 | ✅ 50/50 |
| 数据集与文档交叉 | `data/` 与 man 页 `\alias` 比对 | ✅ 50/50（missing=0） |

### 3.4 本地 R 侧：鸿蒙适配补全测试（test_boot_api.R，195 断言）

覆盖 NAMESPACE 全部 36 个导出函数，使用真实数据集、固定 `set.seed` 保证可复现，
含错误分支与结构/数值断言，绘图重定向临时设备：

| 覆盖组 | 代表函数 | 结果 |
|--------|---------|------|
| 核心自助法 | boot / boot.ci / boot.array / boot.return | ✅ |
| 特殊自助法 | censboot / tsboot / tilt.boot / abc.ci | ✅ |
| 影响函数与诊断 | empinf / linear.approx / jack.after.boot / envelope / norm.ci | ✅ |
| GLM 相关 | cv.glm / glm.diag / glm.diag.plots | ✅ |
| 重要性重采样 | imp.moments / imp.prob / imp.quantile / imp.weights | ✅ |
| 鞍点与工具 | saddle / saddle.distn / simplex / smooth.f / var.linear / k3.linear /
  exp.tilt / nested.corr / corr / cum3 / freq.array / control / logit / inv.logit | ✅ |
| **合计** | **195 断言 / 0 失败** | ✅ |

---

## 四、复现命令

```bash
# 0) 环境（鸿蒙 /tmp 只读）
export TMPDIR=$HOME/tmp

# 1) CI 侧（R-free，等价 CI 门禁）
conan create archives/b/boot/1.3-32 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → build() 与 test_package 各跑一次 validate_boot.py：assertions=229 failures=0

# 2) 本地 CI 模拟（L0/L1/L4/L5）
CI_PACKAGES=archives/b/boot/1.3-32 CI_BRANCH=feat/boot-1.3-32 \
  /usr/bin/zsh ci/conan/build_and_test.sh
# → L0/L1/L4/L5 = pass；Pass rate: 100.0% (1/1)

# 3) 本地 R 侧（自建 R 运行时）
export R_RUNTIME=$HOME/tmp/r-runtime BOOT_WORK=$HOME/tmp/boot-work
sh archives/b/boot/1.3-32/test_package/R/run_local_verification.sh
# → UPSTREAM_EXAMPLES_RESULT=PASS (passed=234/234)
#   UPSTREAM_TESTS_RESULT=PASS
#   API_TESTS_RESULT=PASS (assertions=195 failures=0)
#   TOTAL_PASS_RATE=100.00% (passed=430 total=430)
```

---

## 五、结论

boot 1.3-32 在 HarmonyOS PC（aarch64）适配完成：包树完整、零未发布依赖
（规避 CI L0i hard-fail）、CI 侧 229 项 R-free 断言与本地 R 侧 430 项实测断言
全部通过，**通过率 100%**。上游 R 测试在 CI 不执行的原因（环境无 R 运行时）
已在本报告 §2.4 与 `test_package/MANIFEST.yml` 如实申报。
