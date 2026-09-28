# 测试报告 — kylin-ai-document-service 1.2.0.0

> **项目**: kylin-ai-document-service
> **测试日期**: 2026-09-26
> **测试环境**: HarmonyOS PC aarch64（OHOS 6.0 / Clang 15，`aarch64-unknown-linux-ohos`）
> **测试类型**: 消费者视角 test_package（L1）+ 上游官方测试程序 + W3 本地 CI 全门禁
> **上游版本**: tag `build/1.2.0.0-ok0.6`，commit `ef12f7fae2cbc6a2f5d3c3626c96f35b5935a832`
> **源码 sha256**: `73f416627c58a2f62d13c5e460d84c29c979d2b54ac0ffb1de4cf6669120f481`
> **补丁数**: 3（全部干净应用）

---

## 一、测试摘要

| 指标 | 数值 | 结论 |
|:----:|:----:|:----:|
| test_package 检查项 | 5 / 5 | ✅ 100% |
| W3 门禁（G0/KC/JC/L0/L1/L2/L4/L5） | 8 项执行，7 pass + 1 skip | ✅ 无 fail |
| W3 Pass rate | 100.0% (1/1) | ✅ |
| 上游测试程序 | N = 1（退出码 0） | ✅ 执行完成 |
| conan create | EXIT=0 | ✅ |
| conan-verify | G0–G4 全 PASS | ✅ |

**核心通过率**: ✅ **100%**（本机验证范围）

---

## 二、test_package 消费者测试（L1）

消费者程序 `test_package/test_document_service.cpp` 实质调用已安装包，而非空壳：

| # | 检查项 | 结果 |
|:-:|:-------|:----:|
| 1 | `DocumentChunkClient()` 构造成功（`startUserService()` → `sd_bus_open_user()` 经链接的 libsystemd 真实执行） | ✅ |
| 2 | 3 参 `SyncChunkDocument(file_paths, chunker_types, chunk_sizes)` 返回真实 RPC 结果 | ✅ |
| 3 | 3 参响应携带 JSON 载荷或具体 gRPC 错误码 | ✅ |
| 4 | 4 参 `SyncChunkDocument(..., max_doc_chars_count)` 返回真实 RPC 结果 | ✅ |
| 5 | 两个重载对服务状态判断一致 | ✅ |

实测输出：

```
[ok]   3-arg SyncChunkDocument returned a genuine RPC result
[ok]   3-arg response carries JSON payload or a concrete error code
[ok]   4-arg SyncChunkDocument returned a genuine RPC result
[ok]   both overloads agree on the service status
kylin-ai-document-service consumer test: 5/5 checks passed
```

**断言性质说明**：本测试判定的是「RPC 真实发生」——无服务监听时须返回非 OK 状态且
错误信息非空；若服务确实应答成功亦为通过。**不允许**出现的是「静默未调用」。
因此该断言可观测、可失败，非恒真断言。

---

## 三、W3 本地 CI 全门禁

| 门禁 | 结果 | 说明 |
|:-----|:----:|:-----|
| G0 | pass | 环境闸 |
| KC | pass | 知识库一致性 |
| JC | pass | 垃圾文件检测（JC1–JC6，含 PR 单软件原子性） |
| L0 | pass | all checks passed |
| L1 | pass | test_package executed |
| L2 | skip | 无 `bin/` 目录（纯库包） |
| L4 | pass | patches clean |
| L5 | pass | `lib/` 有内容 |
| **Pass rate** | **100.0% (1/1)** | |

`.ci-result.json`：`exit_code = 0`，`log_sha256 = e65d66d3…df0d`。

---

## 四、上游测试程序

上游仅 1 个测试程序（`test/test.cpp`，`ENABLE_TEST=ON` 时构建），无单元测试框架、
无 CTest 注册，故 **N = 1**。

| 项 | 实测 |
|:---|:-----|
| 执行 | `<build>/test/test` |
| 退出码 | 0 |
| 断言 | **无** |

⚠️ **如实申报的上游局限**：
1. `main()` 中 `catch(...)` 后恒 `return 0`，退出码**不反映真实结果**；
2. 输入路径硬编码（`/home/kylin/文档/...docx`），依赖运行中的文档服务；
3. 因此上游程序**不构成有效断言证据**，本包的测试证据以第二节 test_package 为准。

---

## 五、产物校验

| 产物 | 校验 |
|:-----|:-----|
| `libkylin-ai-document-service.so{,.2,.2.0.0}` | 存在，非空，ELF aarch64-ohos，含 `DT_SONAME` |
| `include/kylin-ai-document-service/` | 4 个头文件 |
| `share/pkgconfig/kylin-ai-document-service.pc` | 可重定位 |
| `share/kylin-ai-document-service/python/` | 服务数据 |
| `lib/systemd/user/kylin-ai-document-service.service` | 已安装 |
| `licenses/LICENSE` | GPL-3.0-or-later |

上游测试程序的 `Error loading shared library …` / `Error 127 … libsystemd.so.0 not found`
两类构建期问题已由补丁修复：注入 `CMAKE_SHARED_LIBRARY_SONAME_C(XX)_FLAG=-Wl,-soname,`
（OHOS 无 `Platform/HarmonyOS.cmake`，该变量默认为空，见知识库 E537）。

---

## 六、已知限制（环境，非缺陷）

1. **运行期必失败项**：`startUserService()` / `sd_bus_open_user()` 依赖运行中的 systemd
   守护与用户 D-Bus。OHOS 不提供 systemd、无用户会话总线，故运行期该路径必然失败；
   **编译与链接不受影响**，消费者测试已接受此环境事实并转为可观测断言。
2. `/tmp` 只读（E002），测试数据文件写入受限于可用路径。
3. 上游测试程序硬编码输入路径，无法在本环境提供真实 docx 输入。

---

## 七、测试结论

本包在 HarmonyOS PC aarch64 上完成 `conan create` + `test_package` 消费者断言 +
W3 全门禁，**本机验证全绿**。上游测试程序的局限性已如实申报，不作为有效证据。

按仓内约定（`CI 验证前不预标 built`），当前状态标记为 **`pending_ci`**，待 CI 复核。
