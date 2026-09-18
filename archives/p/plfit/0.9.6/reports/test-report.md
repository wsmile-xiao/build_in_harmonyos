# 测试报告 — plfit 0.9.6

> **项目**: plfit 0.9.6
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS PC (HongMeng Kernel 1.12.0) aarch64 / clang 15.0.4 / OHOS SDK 26.0.0.18
> **测试类型**: 官方测试套件（上游 CTest）+ 消费者验证（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总检查数 | 28 | 100% |
| 通过 (PASS) | 28 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

（9 项上游 CTest + 11 项消费者 API 检查 + 8 项 CLI 冒烟检查）

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：上游 CTest 9/9、消费者 API 11/11、CLI 冒烟 8/8，全部在 `conan create`（与 CI 同路径）内真实执行。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| CMake 不识别 HarmonyOS 平台（构建期告警） | 无功能影响 | 🟢 |
| HMDFS jobserver fifo EPERM（构建期告警，-j1 规避） | 无功能影响 | 🟢 |

### 2.3 可用功能清单

```
✅ 离散幂律拟合（MLE / LBFGS / LINEAR_SCAN / PRETEND_CONTINUOUS）
✅ 连续幂律拟合（stratified / linear-only）
✅ KS 统计量与 log-likelihood 计算
✅ 矩统计（mean/variance/skewness/kurtosis）
✅ 采样例程（zeta / Pareto / 别名法）
✅ plfit / plgen 命令行工具
✅ CMake 包消费（find_package(plfit) → plfit::plfit）
```

### 2.4 已知限制

1. SWIG Python 绑定未构建（`PLFIT_COMPILE_PYTHON_MODULE=OFF`，OHOS 工具链无 SWIG 依赖链）。
2. `plfit -p exact` 精确 p 值需约 2500 次重采样，耗时较长（上游行为，测试使用默认 SKIP）。
3. `libplfit.pc` 的 `Libs.private: -lm` 为上游生成内容；OHOS 无独立 libm，使用 `pkg-config --static` 的下游需忽略该项（正常 `--libs` 不受影响）。

---

## 三、测试详情

### 3.1 上游 CTest（9/9 PASS，`ctest --output-on-failure`）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_discrete | 离散 MLE（L 值、四种 alpha 方法） | ✅ PASS |
| test_continuous | 连续拟合 | ✅ PASS |
| test_real | 真实数据（karate/celegans/condmat2005） | ✅ PASS |
| test_sampling | 采样例程回归 | ✅ PASS |
| test_underflow_handling | 下溢回归数据 | ✅ PASS |
| test_xmin_too_low | xmin 过低边界（3 用例） | ✅ PASS |
| test_hzeta | Hurwitz zeta 函数 | ✅ PASS |
| test_kolmogorov | KS 统计量 | ✅ PASS |
| test_gss | 黄金分割搜索 | ✅ PASS |

### 3.2 消费者 API 测试（11/11 PASS，test_package）

| 检查项 | 结果 |
|--------|------|
| 安装头文件版本号 = 0.9.6 | ✅ PASS |
| plfit_discrete 成功返回，alpha≈2.49 (目标 2.5)，xmin∈[1,3]，D∈(0,1)，L<0 | ✅ PASS |
| plfit_continuous 成功返回，alpha≈2.02 (目标 2.0)，D∈(0,1) | ✅ PASS |
| plfit_moments 成功返回，方差/峰度 > 0 | ✅ PASS |

### 3.3 CLI 冒烟测试（8/8 PASS，test_package/test.sh）

| 检查项 | 结果 |
|--------|------|
| `plfit -v` / `plgen -v` 输出 0.9.6 | ✅ PASS |
| `plgen -s 42 2000 2.5` 生成 2000 个离散样本 | ✅ PASS |
| `plfit -b` 输出 D 行，拟合 alpha≈2.50 ∈ (2.0, 3.0) | ✅ PASS |
| `plgen -c -s 7 2000 2.0` 生成 2000 个连续样本 | ✅ PASS |
| `plfit -b` 输出 C 行，拟合 alpha≈2.01 ∈ (1.5, 2.5) | ✅ PASS |

### 3.4 跳过的测试

无（上游 test_python_module.py 属 SWIG 绑定，本配方未构建该模块，未计入）

---

## 四、关键问题分析

### 问题1: 链接失败 `-lMATH_LIBRARY-NOTFOUND`

**现象**：
```
ld.lld: error: unable to find library -lMATH_LIBRARY-NOTFOUND
```

**根因分析**：
OHOS sysroot 无独立 libm.so（数学函数由 libc 提供），CMake 又不识别
HarmonyOS 平台，`FIND_LIBRARY(MATH_LIBRARY NAMES m)` 返回 NOTFOUND 并被
原样传入所有链接行（补丁 0001 前）。

**解决方案**：
补丁 0001：`if(NOT MATH_LIBRARY) set(MATH_LIBRARY "") endif()`（zxcvbn-c 2.6
同款先例）。实测 clang 接受 `-lm`，但 CMake 层面无法发现文件，空置最稳。

### 问题2: 静态构建安装后缺少 libplfit.a

**现象**：
`make install` 只安装 bin/include/pkgconfig，无静态库。

**根因分析**：
上游 `install(TARGETS plfit LIBRARY ...)` 未声明 ARCHIVE artifact kind。

**解决方案**：
补丁 0002 追加 `ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}`。

---

## 五、测试环境

```
plfit/0.9.6@ohpcd/stable（静态库 + plfit/plgen CLI）
conan create -pr:h=ohos-aarch64（clang 15, Release, armv8/aarch64）
上游 CTest: 100% tests passed, 0 tests failed out of 9
test_package: consumer 11/11 + CLI smoke 8/8
```

---

*报告生成时间: 2026-09-17*
