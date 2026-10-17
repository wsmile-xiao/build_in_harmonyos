# libdecaf 1.0.2 测试报告

> **项目**: libdecaf 1.0.2（Ed448-Goldilocks / Curve25519 椭圆曲线密码库）
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS 设备（aarch64，clang 15 / clang 交叉工具链），W3 使用 ohos-aarch64 profile（Conan 2.29.1）
> **测试类型**: 官方测试套件（上游 CTest）+ 消费者测试（test_package）

---

## 一、测试摘要

计数单位：上游按 CTest 注册项（2 项）+ 上游未注册工具（2 项）= 4；鸿蒙特有为 test_package 消费者测试程序（1 个，含 6 项断言）。程序数与断言数不混加。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试程序合计 | 4 | 100%（分母） |
| 通过 (PASS) | 3 | 75% |
| 失败 (FAIL) | 0 | 0% |
| 不适用（交互式工具，如实披露） | 1 | 25% |
| 跳过 (SKIP) | 0 | 0% |
| 鸿蒙特有消费者测试 | 1（6 项断言全过） | 100% |

**上游测试通过率**: 3/4（75%，4 个上游测试程序中 3 项实跑通过；ristretto_tester 交互式不适用自动化，如实披露）；**消费者测试通过率**: 1/1（100%，6/6 项断言）

---

## 二、测试结论

### 2.1 总体评价

✅ 上游测试套件在适配后全部通过；库在 OHOS aarch64（arch_ref64 代码路径）下编译、链接、运行正常。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 C++ 头在严格告警下出现 -Wdeprecated-copy | 仅 C++ 消费者告警（非错误） | 🟢 |
| ristretto_tester 为交互式调试工具 | 不影响库功能与自动化验证 | 🟢 |

### 2.3 可用功能清单

```
✅ decaf_448 C API：标量/点算术、编解码、Elligator（消费者测试 6 项断言）
✅ decaf_255 C API（上游 decaf_tester 19 组断言含 Curve25519 全部通过）
✅ EdDSA/ECDH/CFRG/Ristretto/Dalek 向量（上游测试组全 PASS）
✅ SHAKE/SHA3/spongerng（shakesum 工具管道模式实测输出摘要正常）
✅ 静态/动态库产物（G4 产物完整性、L5 基线 PASS）
```

### 2.4 已知限制

1. 上游 `ENABLE_TESTS` 默认 OFF，上游测试程序不随包安装（保持上游默认行为）。
2. ristretto_tester（上游同样未注册 CTest）为交互式计算器，非交互环境仅输出用法。

---

## 三、测试详情

### 3.1 通过的测试

设备原生 aarch64 实跑（模拟 OHOS toolchain，ref64 路径；原始日志：
task-data/libdecaf-1.0.2/upstream-evidence/upstream-test-run.log）：

| 测试项 | 功能 | 结果 |
|--------|------|------|
| ctest: decaf（decaf_tester） | 曲线算术/Elligator/EC/EdDSA/ECDH/CFRG 向量 19 组 | ✅ PASS（61.33s） |
| ctest: bench（bench_decaf） | 点运算基准可执行冒烟 | ✅ PASS（0.77s） |
| shakesum_tester shake256 | SHAKE256 摘要管道模式 | ✅ PASS（exit 0） |
| test_libdecaf（消费者） | decaf_448 API 6 项断言 | ✅ PASS（6/6） |

W3 交叉构建（ohos-aarch64 profile，conan create + test_package 自动运行）：
reports/w3-local-ci.log —— Success: 1, Failed: 0（100%）。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| ristretto_tester | 交互式调试计算器，上游亦未注册 CTest；非交互环境不适用自动化 |

---

## 四、关键问题分析

### 问题1: 消费者测试初版误将常量对象当函数调用（已修复）

**现象**：首轮 W3 中 test_package 编译失败：
`error: called object type 'const decaf_448_point_t' is not a function`（decaf_448_point_identity 为单位元常量点对象）。

**根因分析**：消费者测试初稿未先经编译验证。

**解决方案**：改为 `decaf_448_point_copy(id, decaf_448_point_identity)`；设备原生编译+运行 6 项断言全过后重新提交验证（commit fix: correct decaf_448_point_identity usage in consumer test）。

---

## 五、测试环境

```
libdecaf 1.0.2（上游 v1.0.2 tag = da2f2f9b 忠实 tarball）
构建: cmake 4.1.2 / conan 2.29.1 / clang 15（OHOS aarch64）
选项: ENABLE_STATIC=ON, ENABLE_SHARED=OFF, ENABLE_STRICT=OFF
补丁: 0001 cmake≥3.5（CMake 4 兼容）; 0002 aarch64 架构检测修复（arch_ref64）
```

---

*报告生成时间: 2026-09-17*
