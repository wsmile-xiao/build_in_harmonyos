# aliki 0.3.0 测试报告

> **项目**: aliki
> **测试日期**: 2026-08-31
> **测试环境**: HarmonyOS PC aarch64（OHOS clang 15, ohos-aarch64 profile）
> **测试类型**: 本地 CI 模拟（ci/conan/build_and_test.sh）+ 消费者 test_package

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 2 | 100% |
| 通过 (PASS) | 2 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — aliki 0.3.0 两个可执行（aliki GUI + aliki-rt 实时采集）在 OHOS aarch64 上
编译成功，`conan create` 完整通过（含 test_package 冒烟测试）。

> ⚠️ **关于本地 CI 模拟（build_and_test.sh）的说明**：
> 本地 CI 模拟中，aliki 的 L0i 依赖闸因 **clxclient/3.9.2 尚未发布到制品仓 ohpcd** 而
> 被阻（registry_unreachable）。这是 **R36 依赖链的预期行为**，不是本配方缺陷——clxclient
> 是本次任务先适配的缺失依赖，需先经其自身的 PR → release 流水线发布到制品仓后，aliki 的
> L0i 依赖闸即放行。本地 `conan create` 已用本地缓存中的 clxclient 完整验证编译与测试。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 依赖发布时序（R36） | aliki 的 CI L0i 依赖闸需 clxclient 先发布 | 🟡（预期，按序解决） |

### 2.3 可用功能清单

```
✅ 可执行: aliki（X11 GUI，脉冲响应测量）
✅ 可执行: aliki-rt（实时采集，ALSA/JACK）
✅ aliki -h: 打印 "Aliki-0.3.0" 版本横幅并退出
✅ aliki-rt 无参: 正常返回 1（缺共享内存参数，运行时闭包已加载）
```

### 2.4 已知限制

1. 上游 0.3.0 无任何测试目标/测试目录（`make check` 报 No rule），已如实声明
2. aliki 为 X11 GUI 应用、aliki-rt 需音频硬件与共享内存，无显示/无音频的 CI 环境
   不能跑完主流程，test_package 以「二进制能加载完整运行时闭包并到达正常提前退出路径」
   为通过标准
3. 本包依赖 clxclient/3.9.2，须待其发布到制品仓后，本包 CI L0i 依赖闸方通过

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| conan create | 从干净源码构建 aliki 与 aliki-rt 两个 ELF64/AArch64 可执行 | ✅ PASS |
| test_package/test_aliki.sh | staging 完整运行时闭包 + ELF 签名；aliki -h 输出 "Aliki-0.3.0" 横幅；aliki-rt 无参退出 1（非 127 loader 错误） | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| （本地 CI 模拟 L1-L5） | 本地 CI 模拟在 L0i 依赖闸被阻（clxclient 未发布，R36 预期），conan create 已另行独立验证通过 |

---

## 四、关键问题分析

### 问题1: OHOS toybox sh 不支持 `$(...)` 命令替换

- **现象**: test_package 的 shell 脚本首版用 `banner=$(...)`，OHOS `/system/bin/sh`
  （toybox）报 `syntax error: unexpected '('`
- **根因**: toybox sh 命令替换支持受限
- **解决**: 改为纯管道 `cmd 2>&1 | grep -q` 的 POSIX 写法，避免命令替换与临时文件

### 问题2: test_package 运行时依赖库加载

- **现象**: 直接运行时 `dlopen libclxclient.so.3` 等报 "Error loading shared library"
- **根因**: conan 缓存 .so 未经 OHOS ELF 签名，且工作目录含 `(32)` 需引号包裹
- **解决**: 采用 libxft/clxclient 同款 OHOS 运行时 staging（复制闭包 + 签名 + LD_LIBRARY_PATH），
  并在 self.run 中给脚本路径加引号
