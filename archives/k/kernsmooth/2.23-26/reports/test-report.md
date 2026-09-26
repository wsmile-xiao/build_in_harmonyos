# kernsmooth 2.23-26 测试报告

> **项目**: kernsmooth 2.23-26
> **测试日期**: 2026-09-24
> **测试环境**: HarmonyOS PC (aarch64-unknown-linux-ohos), clang15 + flang 20.1.0 交叉编译
> **测试类型**: 手动功能测试（C 数值测试替代 R 包上游测试）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数（C 断言） | 17 | 100% |
| 通过 (PASS) | 17 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — libkernsmooth.a 静态库编译完成，C 消费者可实质调用 Fortran 核心例程，
数值结果与手算/解析一致。

### 2.2 上游测试不可运行说明（如实申报）

- 上游测试为 R 包测试（`tests/bkfe.R`、`tests/locpoly.R`），需 R 解释器（r-base/4.5.1）
  与 carData 包。本机无 R，且 r-base/4.5.1 未发布到 ohpcd Conan remote（W0 实测），
  **无法运行上游 R 测试**。
- 替代方案：test_package 用 C 程序实质调用 libkernsmooth.a 的 Fortran 符号
  （linbin_、rlbin_、locpol_），以手算数值/解析真值验证，17/17 通过。
- 本包为纯数值 Fortran 计算（无平台相关代码），C 数值测试等价覆盖核心 API。

---

## 三、测试明细

| # | 被测符号 | 测试内容 | 断言数 | 结果 |
|:-:|---------|---------|:------:|:----:|
| 1 | `linbin_` | 一元线性装箱：5 点 X=[0,0.25,0.5,1,1.75] 于 [0,2] 5 格，计数与手算一致 {1.5,1.5,1,0.5,0.5} | 5 | ✅ |
| 2 | `rlbin_` | 回归数据装箱：4 点 (X,Y) 于 [0,3] 4 格，xcnts/ycnts 与手算一致 | 5 | ✅ |
| 3 | `locpol_` | 局部多项式回归（degree=1）：y=x 恒等线，gridsize=10，6 个内点拟合与真值误差 < 1e-6 | 6 | ✅ |
| 4 | `blkest_` | 阻塞多项式估计：y=2x 线性数据，th22e≈0（2 阶导为零的解析预期），链接运行正常 | 1 | ✅ |

## 四、conan create 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` ✅
- G0-G4 + L2/L4/L5 八道门禁全 PASS（见 conan-verify-report.md）
- W3 本地 CI 模拟（setup.sh + build_and_test.sh）：L0/L1/L4/L5 **全 PASS**，
  L1e 破坏性负向测试确认 test 真实依赖 kernsmooth（sabotage lib/include 后测试失败）
- 产物：lib/libkernsmooth.a + include/kernsmooth.h + licenses/LICENCE.note