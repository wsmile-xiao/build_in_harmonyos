# 测试报告 — librtmp 2.4_git20190330

> **项目**: librtmp 2.4_git20190330（rtmpdump git master 快照 c5f04a58）
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS PC 设备（OHOS，aarch64/armv8，clang 15.0.4，libc++，Conan 2.29.1 OHOS 版，profile ci/conan/profiles/ohos-aarch64）
> **测试类型**: 消费者功能测试（test_package，W3 本地 CI 实跑）+ 上游测试清点

---

## 一、测试摘要

统计口径一（测试程序）：上游 0 个，消费者 1 个。
统计口径二（断言数，本报告主口径）：消费者测试程序内 34 处 CHECK 断言。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总断言数 | 34 | 100% |
| 通过 (PASS) | 34 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（34/34）**

上游测试：0/0（不适用——上游 0 个可运行测试入口；上游无 tests/ 目录、无
check/test 目标、无测试框架，清点证据见 test_package/MANIFEST.yml 与 PR 正文）。

---

## 二、测试结论

### 2.1 总体评价

✅ 库在 OHOS 平台交叉编译构建成功，消费者测试实调公开 API 全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| OpenSSL 3.x 对 RC4/DH 低层 API 的 deprecated 编译警告 | 仅告警噪声，功能不受影响 | 🟢 |

### 2.3 可用功能清单

```
✅ RTMP URL 解析: rtmp/rtmpe 协议识别、host/port/app/playpath 提取、非法输入拒绝
✅ AMF0 编解码: Int16/Int24/Int32/Number/Boolean/String 编码-解码回环
✅ 日志分级: RTMP_LogSetLevel/RTMP_LogGetLevel 往返
✅ RTMP 对象生命周期: RTMP_Init 初始化断言、RTMP_Close 空对象安全
✅ 库产物: librtmp.a（默认）构建与打包；shared=yes 路径产 librtmp.so.1
```

### 2.4 已知限制

1. 上游 2019 快照未跟进 OpenSSL 1.1+/3.x API，经
   patches/0001-openssl-1.1-3.x-compat.patch 按版本宏分支适配（对 OpenSSL <1.1
   保留原路径，语义与发行版补丁一致）。
2. 本包仅交付库（不含 rtmpdump/rtmpgw/rtmpsrv/rtmpsuck 命令行工具）；RTMPE/RTMPS
   连接功能经 API 单元消费者测试覆盖（URL/AMF/握手依赖的加密原语编译并链接），
   未做真实网络流媒体连通性测试（无本地 RTMP 服务端环境）。

---

## 三、测试详情

### 3.1 执行方式与证据

- 执行入口: finish 内 W3 本地 CI（`conan create` 默认 variant + test_package
  构建/运行），日志 `reports/conan-create.log`（本轮 W3 日志
  `reports/w3-local-ci.log`，L1_RESULT=pass: test_package executed）。
- 设备实跑输出（conan-create.log 尾部）:
  `RUN: "./test_librtmp"` → `librtmp consumer test: 34 checks, 0 failures`
- 交叉编译: Clang 15.0.4（aarch64-linux-ohos），依赖 openssl/3.5.6 + zlib/1.3.1
  制品仓二进制（W0 已验证 binary 可解析）。

### 3.2 通过的测试（按测试组）

| 测试组 | 断言数 | 功能 | 结果 |
|--------|--------|------|------|
| test_log_level | 3 | 日志分级 WARNING/DEBUG2/ERROR 设置与读取往返 | ✅ PASS |
| test_rtmp_lifecycle | 4 | RTMP_Init 默认值（sb_socket=-1、chunk 128、bufferMS 30000）、RTMP_Close 空对象安全 | ✅ PASS |
| test_parseurl（规范 URL） | 6 | rtmp://example.com:1935/live/stream → protocol/port/host/app/playpath | ✅ PASS |
| test_parseurl（rtmpe URL） | 6 | rtmpe://media.example.org:8080/vod2/mp4:file.mp4 全字段 | ✅ PASS |
| test_parseurl（非法输入） | 2 | 无 :// 与无 host 的 URL 拒绝 | ✅ PASS |
| test_amf_integer | 6 | AMF Int16/Int24/Int32 编码长度与解码回环 | ✅ PASS |
| test_amf_number_boolean_string | 7 | AMF Number/Boolean/String 编解码回环与协议常量 | ✅ PASS |

### 3.3 失败/跳过的测试

无（上游无测试入口，故无上游套件执行记录；0/0 情形已在摘要披露）。

---

## 四、结论

librtmp 2.4_git20190330 在 OHOS 平台适配后，消费者 API 测试 34/34 通过，
核心功能（URL 解析、AMF 编解码、日志、生命周期）可用，达到 built 交付标准。
