# trimal 1.5.1 测试报告

> **项目**: trimal (trimAl) 1.5.1
> **测试日期**: 2026-09-26
> **测试环境**: HarmonyOS PC（HarmonyOS 6.1.0 / HongMeng Kernel 1.12.0 aarch64，HAD-W32）
> **工具链**: OHOS SDK clang/clang++ 15.0.4（target aarch64-linux-ohos）
> **测试类型**: 上游官方数据集回归套件（层 1，集成于 conanfile.build()）+ 消费者测试 test_package（层 2）

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游回归用例总数（84 输入 × 6 模式） | 504 | 100% |
| 通过 (PASS) | 504 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 消费者断言（test_package，鸿蒙特有） | 10 | 100% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **通过**。三个交付二进制（trimal/readal/statal）在 HarmonyOS PC aarch64 上构建、
运行正常；上游 dataset 回归套件 504/504 与参考输出逐字节一致；消费者测试 10/10 断言通过；
负向控制（缺失输入）按预期以非零状态退出。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | — | — |

### 2.3 可用功能清单

```
✅ trimal：自动修剪（gappyout/strict/strictplus/automated1）、手动修剪（-gt/-st/-ct、
         -selectcols/-selectseqs）、nogaps/noallgaps、比对格式读写与转换
✅ readal：比对读取、-info 统计、格式互转（fasta/clustal/phylip/nexus/mega/pir/nbrf 等）
✅ statal：列/序列统计（-sgc/-sgt/-ssc/-sst/-sident/-sfc/-sft 等）
```

### 2.4 已知限制

1. 上游 generate 脚本在部分极端输入上会打印 `WARNING: Removing sequence ... composed only by gaps`
   与 `WARNING: Output alignment has not been generated. It is empty`；这是上游既有行为
   （参考输出同样为空），`compare_trimmed_msas.sh` 仍通过，适配未改动。

---

## 三、测试详情

### 3.1 上游数据集回归套件（层 1，504/504 PASS）

- 来源：`.github/workflows/build.yml`（test_ubuntu_x86_64 job）
  `tar -xvf source/source_bin.tar -C source && source/trimal && ./scripts/generate_trimmed_msas.sh && ./scripts/compare_trimmed_msas.sh`
- 清点：上游无 `tests/` 目录、无 ctest/pytest 注册、Makefile 无 `check` 目标；回归以
  `dataset/` 参考比对实现 —— 84 个输入比对 × 6 种模式（gappyout/strict/strictplus/
  automated1/nogaps/noallgaps）= 504 个用例，逐一与 `dataset/trimmed_msas/<mode>/`
  参考输出 `diff`，任一不同即失败。
- 实机执行（本地构建的 aarch64 二进制）：
  - `generate_trimmed_msas.sh`：exit 0，生成 504 个 MSA（1143s）
  - `compare_trimmed_msas.sh`：exit 0，`Compared ...` × 504，零失配（42s）
  - 日志：`reports/upstream-tests.log`（精简证据版：完整 generate 输出约 7.2k 行上游 WARNING 噪声已省略，保留 504/504 比对结论与首尾样本；完整输出可用 `run_upstream_tests.sh` 重现）
  - 重现脚本：`run_upstream_tests.sh`（自包含：下载官方 tar → make → generate → compare）
- 该套件已集成进 `conanfile.py` 的 `build()`，`conan create`（W3 与平台 CI）时自动复跑。

### 3.2 消费者测试（层 2，test_package，10/10 PASS）

| # | 断言 | 结果 |
|---|------|------|
| 1 | `trimal --version` 输出含 `trimAl v1.5` | ✅ PASS |
| 2 | `trimal -nogaps` 输出与手工核对期望（全列具缺口→`AGT`）逐字节一致 | ✅ PASS |
| 3 | `trimal -gt 0.6` 输出与手工核对期望（`ACGT/A-GT/ACGT/ACGT`）逐字节一致 | ✅ PASS |
| 4 | 负向控制：输入文件不存在时 `trimal` 以非零状态退出 | ✅ PASS |
| 5 | 负向控制：错误信息含 `ERROR` | ✅ PASS |
| 6 | `readal -info` 输出含 `Total sequences` | ✅ PASS |
| 7 | `readal -info` 序列数 = 4 | ✅ PASS |
| 8 | `readal -info` 比对长度 = 5 | ✅ PASS |
| 9 | `statal -sgc` 第 1 列缺口率 = 50% | ✅ PASS |
| 10 | `statal -sgc` 第 2 列缺口率 = 25% | ✅ PASS |

测试数据：`test_package/tiny.fasta`（4 序列 × 5 列，含 2 个含缺口列；期望输出
`expected_nogaps.fasta`、`expected_gt.fasta` 已经与手工推导逐字节核对）。

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无。

---

## 四、关键问题分析

### 问题1: 上游 Makefile 硬编码 `CC = g++`

- 根因：上游仅面向桌面 GCC。
- 解决：`make CC=<conan tools.build:compiler_executables.cpp> -j1`，零源码补丁（R1/R33）。

### 问题2: 上游测试脚本无 shebang 且需执行 ELF

- 根因：GitHub Actions 以 bash 执行；OHOS `/system/bin/sh`(mksh) 不能执行 ELF。
- 解决：`build()` 内显式 `bash scripts/...`（`CONFIG_SHELL` 优先）。

---

## 五、conan create（W3）与 CI 结果

### 5.1 本地 conan-verify（G0–G4 + L2/L4/L5）

- 命令：`python3 scripts/ohc-run.py conan-verify trimal 1.5.1 --profile ohos-aarch64-device`
- 结果：✅ PASS（G0/G1/G2/G3/G4 全通过；L2/L4/L5 因纯可执行包无 cache 路径被验证器跳过）
- G2 的 `conan create` 内部已复跑上游 dataset 回归套件（504 用例）并通过
- 报告：`reports/conan-verify-report.md`；构建日志：`reports/conan-create.log`

### 5.2 Staging 验证

conan 包内 `bin/` 三个二进制逐一 `--version`：trimal / readal / statal 均 OK（3/3）；
标记文件 `.staging-verified`（`verified=3 failed=0`）。

### 5.3 release 打包

`packaging/trimal-1.5.1-ohos-aarch64.tar.gz`（由 conan package 目录打包，含 bin/ 与 licenses/；
sha256 `c423f20dedbd22a2e303ceaa6d75545de21d1212ec5e6314b5f9798a7c495ac3`）。

### 5.4 W3 (.ci-result.json) 与平台 CI

- W3 本地 CI 模拟（finish step [5/10]）：✅ 通过
  - `L0_RESULT=pass`（含 JC 垃圾文件门禁）、`L1_RESULT=pass`（test_package 实际执行）、
    `L1e: Negative test confirmed`（破坏性反向验证确认测试真实依赖被测包）、
    `L2_RESULT=pass`（三个二进制 --version）、`L4_RESULT=pass`（补丁/安全静态检查）、
    `L5_RESULT=pass`（bin/ 产物存在）
  - 结果文件：`.ci-result.json`（exit_code=0，含日志 SHA256）；日志：`reports/w3-local-ci.log`
- W4 独立审计：✅ 通过（verdict=pass，P0/P1=0；4 条 P3 建议已记录，见 `reports/audit-result.json`）
- 平台 CI 与 AI 检视：PR 提交后由平台评论触发（`/rebuild`、`/ai review`），结论以 PR 页面为准。
