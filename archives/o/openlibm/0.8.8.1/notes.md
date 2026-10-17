# openlibm 0.8.8.1 适配笔记

## 编译环境
- 构建系统: makefile（Makefile + Make.inc，无 configure；CMakeLists.txt 为次级）
- 编译日期: 2026-09-20
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-unknown-linux-ohos)
- 状态: published

## 版本说明

`0.8.8.1` 基于上游 tag v0.8.8（与已合并的 0.8.8 同源码、同配方），适配修复后缀用于补齐
**上游测试验证证据**：合并进 main 的 0.8.8 归档缺 `reports/test-report.md`（R51 合规缺口），
本版本在隔离工作区用同一 OHOS 工具链真实复验全量上游测试并补全测试报告。R37 要求
制品仓已存在同版本时适配修复须升后缀版本，故提交 0.8.8.1。

## 编译步骤

```bash
# 1. 源码：官方 tag v0.8.8（sha256=721bab18ff37160fd9e903eb211ff26fdee38c3d0041d556b07d76089c435d17 已核验）
# 2. 交叉构建（OHOS clang 默认目标即 aarch64-unknown-linux-ohos，无需 --target）
make CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib -j2
# 3. 上游测试（完整套件：test-double + test-float + regression 自动收集）
make test CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar RANLIB=/data/service/hnp/bin/llvm-ranlib -j2
# 4. Conan 配方（静态默认，shared=False）
python3 scripts/ohc-run.py conan-verify openlibm 0.8.8.1   # G1-G4 全过
python3 scripts/ohc-run.py finish openlibm 0.8.8.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tools.build:compiler_executables:c` 报不存在 | Conan 2 该 conf 为 dict 类型，不能用 `:c` 后缀路径读取 | 改为 `self.conf.get(..., check_type=dict)` 后 `.get("c")`（沿用 0.8.8） |
| 2 | conan create 报 `No targets specified and no makefile found` | openlibm 原地构建，但 conan 默认 cwd 是空 build 目录 | build() 内 `cwd=self.source_folder`（沿用 0.8.8） |
| 3 | test_package 找不到 openlibm.h | 头文件装在 `include/openlibm/` 子目录 | `cpp_info.includedirs=["include/openlibm"]`（沿用 0.8.8） |
| 4 | 消费者运行报 `Error loading shared library libopenlibm.so.4` | 动态库在 OHOS HMDFS 加载路径不可解析 | 默认 shared=False 静态构建+安装（R26 思路，沿用 0.8.8） |
| 5 | 0.8.8 合并归档缺 `reports/test-report.md` | 0.8.8 提交流程未落测试报告（R51 缺口） | 0.8.8.1 补齐本次实测 4075/4075 全量测试报告 |
| 6 | 回归 test-222/252/334 返回 exit 77 | 上游 `#if LDBL_MANT_DIG != 64`（222/334）与 `#if !defined(__riscv) ...`（252）架构守卫，aarch64 声明"不适用" | 确认非失败：探针实测 LDBL_MANT_DIG=113、非 RISC-V，skip 属上游设计内 |

## 依赖版本

无外部依赖（openlibm 是独立 libm 实现）。构建依赖：OHOS SDK clang 15.0.4 / llvm-ar / GNU make 4.4.1 / conan 2.29.1。

## 验证结果

上游测试实测 **4075/4075 通过（100%）**，0 失败：
- test-double：2050（1118 用例 + 932 异常标志）
- test-float：2024（1101 用例 + 923 异常标志）
- regression/test-211：1（powf 精度）
- regression/test-222/252/334：上游架构守卫显式 SKIP（exit 77，非失败）
鸿蒙专项 test_package 13/13 通过；conan create G1-G4 全过；test_package ctest 1/1 通过。详见 `reports/test-report.md`。

## 注意事项

- openlibm 的 `make all` 同时产静态与动态库；OHOS 消费者优先静态（R26 同源思路），避免 HMDFS 上 DT_NEEDED 绝对路径/SONAME 解析问题。
- `include/openlibm/` 为头文件根目录（与其 .pc 一致），消费者 include 路径需含该子目录。
- 上游测试用 `make test`（test-double + test-float + regression）；libm-bench 是基准非测试；inf_torture 上游未接入 test 目标。
- aarch64 上 `LONG_DOUBLE_NOT_DOUBLE=1`，ld128/ 树参与编译，long double 为 128 位（与 x86 80 位不同）。
---

**编译结束**: 2026-09-20
**最终状态**: published
