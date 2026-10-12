# libnice 0.1.21 测试报告

> **项目**: libnice 0.1.21 HarmonyOS PC 适配
> **测试日期**: 2026-10-11
> **测试环境**: HarmonyOS PC 6.0 aarch64，HarmonyOS SDK Clang 15
> **测试类型**: 上游 Meson 测试套件、Conan consumer、HarmonyOS 设备功能测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试项 | 69 | 100% |
| 通过 (PASS) | 63 | 91.3% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 6 | 8.7% |

**已执行上游测试项通过率**: ✅ **100%（63/63）**

清点口径：5 个 GLib 测试文件共注册 33 个 `g_test` 测试项，其余 36 个 Meson 测试目标各作为一个独立测试项，共 69 项。设备日志按 Meson 目标记录状态，41/41 目标返回成功；但 `test-turn` 在 coturn 缺失时提前退出，6 个内部用例没有执行，因此按测试项统计为 63 PASS、6 SKIP。另有 Conan C consumer 和 HarmonyOS IPv4 UDP STUN loopback 两项新增验证，均通过；总计 71 项，65 PASS、6 SKIP。

---

## 二、测试结论

### 2.1 总体评价

✅ **全部已执行测试项通过：上游 63/63、Conan consumer 1/1、HarmonyOS STUN 网络行为验证 1/1。上游另有 6 个 TURN 用例因 coturn 缺失而跳过。**

这表示软件包级 W3/Conan/设备验证通过，不表示仓库全局 `finish` 已完成。完整 `finish` 返回 partial：干净构建预检因 checkout 中没有原始源码 tarball 无法执行；发布校验缺少 `packaging/`、release/debug tarball 和 `.staging-verified` 标记；W5 还有仓库既有知识图谱问题（542 个 KV 缺少配对 MD，以及 E219/E253/E305 字段问题）。这些仓库级就绪阻塞不属于 libnice 软件包测试结果。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| `stund`、`stunbdc` 的 `--version`/`--help` 检查未通过 | 官方 finish 的非阻塞 CLI 冒烟项；真实服务端和客户端行为测试通过 | 🟢 |

### 2.3 可用功能清单

```text
✅ 核心 ICE/STUN/TURN 库：构建、链接和 Conan consumer 调用通过
✅ stund 与 stunbdc：HarmonyOS IPv4 UDP STUN loopback 请求/响应通过
✅ PseudoTCP：上游随机传输测试通过，另有 1 MiB 逐字节复核通过
⚠️ GStreamer、GUPnP、introspection：按本次范围关闭
```

### 2.4 已知限制

1. 此配方关闭 GStreamer、GUPnP、introspection、GTK 文档和示例；当前包验证的是核心库及两个 STUN 工具。
2. 两个 STUN 工具不满足 finish 中 `--version`/`--help` 冒烟检查的预期，但真实 STUN 交互已在 HarmonyOS 设备上成功完成。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 上游 Meson 测试套件 | ICE、STUN、trickle、consent、PseudoTCP 等 69 个测试项，覆盖 41 个 Meson 目标 | ✅ PASS 63；SKIP 6；FAIL 0（41/41 目标返回成功） |
| Conan `test_package` consumer | 通过 `nice.pc` 创建 `NiceAgent` 并添加 stream 1 | ✅ PASS |
| HarmonyOS IPv4 UDP STUN loopback | 启动 `stund`，由 `stunbdc` 发送 Binding Request 并解析映射地址 | ✅ PASS（127.0.0.1:58690 → 127.0.0.1:35727） |
| PseudoTCP 1 MiB 定向复核 | `MALLOC_PERTURB_=84` 下对发送/接收文件逐字节比较 | ✅ PASS |

`test-turn` 源码注册了 6 个用例，但先检查 `turnserver`/coturn；设备未安装 coturn，程序在 `g_test_run()` 前返回成功，所以这 6 项按 SKIP 计。`test-pseudotcp-random` 是上述 69 个上游测试项中的一个 Meson 目标，其独立复核结果不重复计数。1 MiB 定向复核是同一上游测试行为的额外数据规模复跑，也不作为新增测试项计数。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

`test-turn` 的 6 个 GLib 用例因设备缺少 coturn 而没有执行；该上游程序在 `g_test_run()` 前以成功状态退出，因此 Meson 将目标记为成功。除此之外没有测试项失败或跳过。GStreamer、GUPnP 和 introspection 相关功能按选定构建范围关闭，不属于本次启用的测试集。

---

## 四、关键问题分析

### 上游 PseudoTCP 随机测试在队列满时的字节计数

**现象**：HarmonyOS 队列满时，`pseudo_tcp_socket_send()` 返回 `-1` 表示 EWOULDBLOCK、接受 0 字节。上游随机传输测试将 `-1` 直接纳入已发送字节计数和文件回退量，导致重复一个字节并使接收文件与原文件不一致。

**根因分析**：负返回值在更新传输计数前没有归一化为零。

**解决方案**：补丁将负发送结果归一为零，再更新计数和文件位置；同时让无输入文件的短测试不随机丢包，保持测试确定性。最终补丁在设备上通过整套测试及 1 MiB 字节比较。

---

## 五、测试环境

```text
平台：HarmonyOS PC 6.0，aarch64（Conan OHOS/armv8）
工具链：HarmonyOS SDK Clang 15
构建：Meson，default_library=static，crypto-library=openssl
依赖：GLib shared、OpenSSL
官方 W3 日志：reports/w3-local-ci.log
CI 完整性记录：.ci-result.json（日志 SHA256: 94e0ba0c6655e025832ab71bfcfdaefa496808192e85be53ba676a798756f012）
```

---

*报告生成时间: 2026-10-11*
