# 测试报告 — retry 1.0.6（HarmonyOS PC / aarch64）

> **项目**: retry 1.0.6（https://github.com/minfrin/retry）
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0 aarch64（HAD-W32），OHOS SDK clang 15.0.4
> **测试类型**: 上游测试清点（0 用例）+ 消费者功能测试（test_package，28 条断言）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试总数 | 0 | — |
| 上游通过 (PASS) | 0 | — |
| 适配新增测试总数 | 28 | 100% |
| 新增通过 (PASS) | 28 | 100% |
| 新增失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（28/28）**

> 上游 retry 1.0.6 **不含任何测试套件**：无 tests/ 目录、Makefile.am 仅 `bin_PROGRAMS = retry`
> （无 TESTS/check_PROGRAMS/check-local）、configure 无测试开关，`make check` 实测执行 0 用例
> （R51 清点证据见 `test_package/MANIFEST.yml` 与 `notes.md`）。按 R51「上游无测试」场景，
> 由 `test_package/test_retry.sh` 补 28 条消费侧功能断言。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。包可用、可安装、行为符合上游文档；28/28 消费者断言通过，包含 CI L1e
破坏性反向验证（移除 bin/ 后测试必须失败，实测确认测试真实依赖被测二进制）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无（3 个补丁为可移植性修复，已在 clean 构建中验证） | — | 🟢 |

### 2.3 可用功能清单

```
✅ 条件重试: success/true/fail/false、整数、整数区间（可逗号分隔）
✅ --times 次数上限与 --delay/--jitter 退避（含逗号分隔递增序列）
✅ stdin 捕获与重放（恰好一次，可嵌入管道）
✅ stdout 路由：仅成功尝试的 stdout 进入 stdout，失败尝试转入 stderr
✅ 退出码透传；无法执行/非法参数返回 1
✅ -m 自定义退避通知；-v/--help
✅ man 手册安装（share/man/man1/retry.1）
```

### 2.4 已知限制

1. 上游无测试套件，回归保护依赖本包新增的 `test_package/test_retry.sh`（28 断言）。
2. `retry` 设计上会捕获 stdin 并重放，自动化脚本中调用需显式 `</dev/null`（上游行为，非缺陷）。

---

## 三、测试详情

### 3.1 通过的测试（test_package/test_retry.sh，28/28）

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | retry 二进制已安装并在 PATH 上 | ✅ PASS |
| 2 | `retry -v` 退出码 0 | ✅ PASS |
| 3 | `retry -v` 输出 "retry 1.0.6" | ✅ PASS |
| 4 | `retry --help` 退出码 0 | ✅ PASS |
| 5 | `--help` 含 "Repeat command until a criteria" | ✅ PASS |
| 6 | 首次即成功：退出码 0 | ✅ PASS |
| 7 | 首次即成功：stdout 透传 | ✅ PASS |
| 8 | 首次即成功：无退避重试 | ✅ PASS |
| 9 | `--until=success` 最终成功退出码 0 | ✅ PASS |
| 10 | `--until=success` 第 3 次尝试成功（计数=3） | ✅ PASS |
| 11 | 成功尝试的 stdout 进入 stdout | ✅ PASS |
| 12 | 失败尝试 stdout 不泄漏到 stdout | ✅ PASS |
| 13 | 退避通知在 stderr | ✅ PASS |
| 14 | `--times` 耗尽返回退出码 1 | ✅ PASS |
| 15 | "giving up." 提示 | ✅ PASS |
| 16 | 退出码透传（42） | ✅ PASS |
| 17 | stdin 重试运行退出码 0 | ✅ PASS |
| 18 | 首次尝试收到捕获的 stdin | ✅ PASS |
| 19 | 重试尝试收到重放的完整 stdin | ✅ PASS |
| 20 | `--until=fail` 以失败码退出 | ✅ PASS |
| 21 | `--until=fail` 首次失败即停（计数=1） | ✅ PASS |
| 22 | `--while=fail` 对立即成功的命令不重试 | ✅ PASS |
| 23 | 非法 `--while` 退出码 1 | ✅ PASS |
| 24 | 非法 `--while` 有诊断信息 | ✅ PASS |
| 25 | 不可执行命令退出码 1 | ✅ PASS |
| 26 | 不可执行命令有 "Could not execute" 提示 | ✅ PASS |
| 27 | `-m custom-msg` 运行退出码 0 | ✅ PASS |
| 28 | `-m` 自定义消息出现在退避通知中 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（上游 0 用例，无需跳过）。

---

## 四、关键问题分析

### 问题1: `configure: error: cannot guess build type; you must specify one`

**现象**：
```
UNAME_MACHINE = "aarch64"
UNAME_RELEASE = "HongMeng Kernel 1.12.0"
UNAME_SYSTEM  = "HarmonyOS"
configure: error: cannot guess build type; you must specify one
```

**根因分析**：
上游发行包自带 2018 年版 `config.guess`，不认识 `HarmonyOS`。native 构建（build == host）时
AutotoolsToolchain 不传 `--host/--build` 三元组，configure 只能走 `config.guess`。

**解决方案**：
补丁 `0001-build-aux-config.guess.patch`：增加 HarmonyOS 分支输出 `aarch64-unknown-linux-ohos`。
配套补丁 `0002-build-aux-config.sub.patch` 让同版本 `config.sub` 接受 `linux-ohos`
（maybe_os 与大 OS 列表两处），覆盖交叉构建 `--host=aarch64-linux-ohos` 场景。

### 问题2: HMDFS 上 config.status 临时目录不可写（E011）

**现象**：设备 HMDFS 上 `umask 077` 创建的 `confXXXXXX` 临时目录对构建进程不可写。

**根因分析**：HMDFS UID 映射使 0700 目录的 owner 与构建进程 UID 不一致。

**解决方案**：
补丁 `0003-configure.patch`：config.status 临时目录创建 umask 放宽为 022
（与 aaphoto/lrcalc 同一已验证先例）。

---

## 五、测试环境

```
OS:        HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64 (HAD-W32)
Compiler:  OHOS SDK clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
Conan:     2.29.1 (OHOS-adapted)
Profile:   ohos-aarch64-device
Source:    retry-1.0.6.tar.gz (sha256 c208baf759134da27012042ccc30df7d995ed038d7d5602db7dbda3becb34827)
Artifacts: bin/retry; share/man/man1/retry.1
```

**验证链路**（全部在本机实测）：
- `conan-verify`：G0–G4 + L2/L4/L5 全 PASS（reports/conan-verify-report.md）
- 本地 CI 门禁 `ci/conan/build_and_test.sh`：L0 pass、L1 pass（含 L1a/L1b/L1c/L1e）、L2 pass、L5 pass；
  L4 warn 为补丁文本扫描的已知良性命中（config.guess/config.sub 中的 shell 片段，无危险调用）
- `conan create`（clean）日志内 test_package：`# passed: 28, failed: 0`

---

*报告生成时间: 2026-09-18*
