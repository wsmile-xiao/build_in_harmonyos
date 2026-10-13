# Conan Verify Report — phyx 1.3.2

**Verdict**: PASS
**Reference**: `phyx/1.3.2`
**Profile**: `ohos-aarch64`
**Date**: 2026-10-12

## 配方与源码

- 官方源码：`https://github.com/FePhyFoFum/phyx/archive/refs/tags/v1.3.2.tar.gz`
- SHA256：`2c4a80c73b8bbf2117c4a4686655c19f9e0a1f81921cd1ad201b1933e1c6ad14`
- Conan 从干净源码执行 `source()`、补丁应用、构建、打包和 `test_package`。
- `config.guess` 原生输出 `aarch64-unknown-linux-ohos`，configure 明确报告
  `cross compiling... no`，没有使用 `--host`/`--build` 绕过运行探针。

## 构建与打包

- `conan create`：PASS，退出码 0。
- CI 同入口 `build_and_test.sh`：PASS，退出码 0；`config.status` 在 HMDFS 上
  成功生成 `Makefile` 与 `config.h`。
- 依赖：`armadillo/12.8.4`、`nlopt/2.11.0`；构建工具：`automake/1.18`。
- 47 个 CLI、47 份 man page 和官方 TEST 数据完成打包。
- 单数学后端检查：PASS；无禁止的 reference BLAS/LAPACK/FortranRuntime
  动态依赖，无嵌入 `dgemm_`、`dgesv_`、`dgetrf_`。

## 测试

- 上游 runner：执行 100 项；95 项精确匹配，5 项由上游声明为随机预期差异；
  `FAILED PROGRAMS: 0`，命令退出码 0。
- 消费者与 HarmonyOS 专项：4/4 PASS。
- 路径 B 三臂链接实证：A 失败、B 假修复成功但双提供者、C 单提供者成功，结果符合预期。

## 证据完整性

原始真机日志存放在仓库外：

```text
.task-results/phyx-1.3.2/logs/native-conan-ci-fix-r5.log
SHA256: 7c3cbdf269cb1490f297b4687a3a5ce0ef4492d07cd3886d4a260728e9a96540
W3 log SHA256: eccdf65e1d44cdd84b320d1238cb876928661eab3bb387a1901de10b9b5ecf05
Conan recipe revision: 8c3f7476b102ca2185ea9a09dfbde65d
```

该日志由最终配方生成，导出记录同时列出 0001、0002 两个补丁，并记录上述
recipe revision；提交中不包含原始日志或个人绝对路径。
