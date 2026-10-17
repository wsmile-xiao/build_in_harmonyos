# weupnp 0.1.4 测试报告

> **项目**: weupnp
> **测试日期**: 2026-10-01
> **测试环境**: OpenHarmony（`os.name=harmonyos`, `hongmeng kernel 1.12.0`, `aarch64`）+ BiSheng JDK 17.0.13
> **测试类型**: 补全功能测试（消费者视角，对**已打包** JAR）+ 上游可运行样例执行

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 23 | 100% |
| 通过 (PASS) | 23 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

**鸿蒙特有用例**: **3**（OHOS_01 / OHOS_02 / OHOS_03，3/3 通过）—— 满足「鸿蒙特有用例数量 ≥ 1」

**上游自动化测试**: **0 项**（上游 0.1.4 无测试入口，清点证据见 `upstream-verification.md`；
上游构建自身输出 `[INFO] No tests to run.`）。上游**唯一可运行样例** `Main` 已实际执行（见 §3.4）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。weupnp 0.1.4 在 OHOS + BiSheng JDK 17.0.13 上构建、打包、消费全链路可用：
23 个用例覆盖值对象、SAX 解析层、IGD 设备描述解析状态机、SOAP 协议层（6 个 UPnP 动作 + 错误路径 +
HTTP 设备描述加载）、发现层与上游 demo 入口，全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | — | — |

（本版本唯一需要修改的是构建文件编译级别，已由 `patches/0001-pom.xml.patch` 修复，见 `notes.md`。）

### 2.3 可用功能清单

```
✅ PortMappingEntry 值对象（7 个属性读写）
✅ NameValueHandler SAX 名称/值解析（含重复元素拼接）
✅ GatewayDeviceHandler IGD 设备描述解析 + CIF/WANIPConnection 服务状态机
✅ GatewayDevice SOAP 层：GetStatusInfo / GetExternalIPAddress / AddPortMapping /
   GetSpecificPortMappingEntry / GetGenericPortMappingEntry / GetPortMappingNumberOfEntries /
   DeletePortMapping
✅ GatewayDevice UPnP 错误路径（HTTP 500 + <errorCode>）
✅ GatewayDevice.loadDescription()（HTTP 拉取描述 + 相对 URL 按 URLBase 解析）
✅ GatewayDiscover 构造器 / 超时 API / 真实 SSDP 发现
✅ 上游 demo 入口 org.bitlet.weupnp.Main
✅ OHOS 平台：JVM 身份、SSDP 组播传输、产物字节码/OSGi 头可加载
```

### 2.4 已知限制

1. 真机环境无 UPnP IGD，故 `GatewayDiscover.discover()` 实测返回 0 个网关（属预期，非失败）——
   发现链路的 **socket/组播发送/超时等待** 均已真实执行且无异常。
2. SOAP 动作的**响应解析**通过本地 mock IGD（`com.sun.net.httpserver`）验证；真实 IGD 的
   设备差异（个别厂商非标字段）不在本测试范围内。
3. CI 环境无 `mvnw`，构建期需访问 `archive.apache.org` 与 `repo.maven.apache.org`。

---

## 三、测试详情

### 3.1 用例与结果（23/23 PASS）

| # | 用例名 | 验证内容 | 结果 |
|---|--------|----------|------|
| 1 | `PortMappingEntry_setters_getters` | 7 个属性 set/get 往返 | ✅ PASS |
| 2 | `NameValueHandler_parses_name_value_xml` | 真实 SAX 解析 `<name>value</name>` → map | ✅ PASS |
| 3 | `NameValueHandler_concatenates_repeated_names` | 同名重复元素拼接（`x`+`y`+`z` → `xyz`） | ✅ PASS |
| 4 | `GatewayDeviceHandler_parses_igd_description` | 设备描述字段（friendlyName/manufacturer/modelName/…/URLBase） | ✅ PASS |
| 5 | `GatewayDeviceHandler_service_state_machine` | WANCommonInterfaceConfig → CIF 槽位、WANIPConnection → 主槽位 | ✅ PASS |
| 6 | `GatewayDevice_simpleUPnPcommand_soap_envelope` | SOAP 信封/参数编组 + `SOAPAction`/`Content-Type` 头 + 响应解析 | ✅ PASS |
| 7 | `GatewayDevice_isConnected_true` | `GetStatusInfo` → `NewConnectionStatus=Connected` | ✅ PASS |
| 8 | `GatewayDevice_getExternalIPAddress` | `GetExternalIPAddress` → `203.0.113.7` | ✅ PASS |
| 9 | `GatewayDevice_addPortMapping_request_args` | `AddPortMapping` 8 个入参全部正确编组 | ✅ PASS |
| 10 | `GatewayDevice_getSpecificPortMappingEntry` | 指定映射条目回填（6 字段） | ✅ PASS |
| 11 | `GatewayDevice_getGenericPortMappingEntry` | 按索引取映射条目回填（7 字段） | ✅ PASS |
| 12 | `GatewayDevice_getPortMappingNumberOfEntries` | 映射条目计数 = 3 | ✅ PASS |
| 13 | `GatewayDevice_deletePortMapping` | `DeletePortMapping` 动作与返回值 | ✅ PASS |
| 14 | `GatewayDevice_upnp_error_response` | HTTP 500 + `<errorCode>606</errorCode>` → 解析错误码并返回 false | ✅ PASS |
| 15 | `GatewayDevice_loadDescription_http` | HTTP 拉取设备描述 + 相对 URL 按 URLBase 解析 | ✅ PASS |
| 16 | `GatewayDevice_http_read_timeout_api` | 默认 7000ms，set/get 生效 | ✅ PASS |
| 17 | `GatewayDiscover_constructors_and_constants` | 3 个构造器 + `PORT=1900`/`IP=239.255.255.250` | ✅ PASS |
| 18 | `GatewayDiscover_timeout_api` | 默认 3000ms，set/get 生效 | ✅ PASS |
| 19 | `GatewayDiscover_discover_live_network` | 真实 SSDP 发现（socket 建/发/超时等待），返回非 null Map | ✅ PASS |
| 20 | `Upstream_Main_entrypoint` | 上游 demo 入口 in-process 执行，无异常 | ✅ PASS |
| 21 | **`OHOS_01_platform_jvm_identity`** | OHOS 平台 JVM 身份（`os.name=harmonyos`、`arch=aarch64`、JDK≥17、BiSheng） | ✅ PASS |
| 22 | **`OHOS_02_ssdp_multicast_transport`** | OHOS 网络栈上的 SSDP 组播发送/超时/关闭 | ✅ PASS |
| 23 | **`OHOS_03_packaged_jar_loads_on_ohos_jvm`** | 已安装 JAR 的 6 个类可被 OHOS JVM 加载 + 字节码 major ≤ 52 + OSGi 头/license | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| — | — | 无失败用例 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| — | 无跳过用例（`discover()` 与 SSDP 发送在本机均正常执行） |

### 3.4 上游可运行样例执行

| 入口 | 命令 | 结果 |
|---|---|---|
| `org.bitlet.weupnp.Main` | `java -jar weupnp-0.1.4.jar` | `EXIT_CODE=0`，9s；输出 `Starting weupnp` → `Looking for Gateway Devices...` → `No gateways found` → `Stopping weupnp` |

---

## 四、测试命令与日志

```bash
# 1) 本地（对准手工构建的 JAR）
$ sh test_package/test.sh ~/bishengjdk17/bin/java ~/bishengjdk17/bin/javac \
      <stage>/libexec/weupnp-0.1.4.jar . <workdir>
total=23 passed=23 failed=0 skipped=0 ohos_cases=3 ohos_passed=3 exit=0
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 23,
  "passedCount": 23, "ohosCases": 3, "ohosPassed": 3, "command": "sh test.sh",
  "reason": "all_cases_passed_23_of_23_with_0_skipped"}

# 2) conan create 内嵌执行（正式门禁路径）
$ python3 scripts/ohc-run.py conan-verify weupnp 0.1.4
weupnp/0.1.4@ohpcd/stable (test package): Running test()
total=23 passed=23 failed=0 skipped=0 ohos_cases=3 ohos_passed=3 exit=0
✅ 配方验证通过: weupnp 0.1.4      EXIT_CODE=0
```

| 日志 | 路径 |
|---|---|
| conan create 完整日志（含 test_package 全量输出） | `reports/conan-create.log` |
| conan-verify 8 门禁报告 | `reports/conan-verify-report.md` |
| 上游/源码核验记录 | `reports/upstream-verification.md` |
| 本地套件运行日志 | `$HOME/tmp/weupnp/logs/20-testpackage-1.log` |
| 首次构建失败（首错）日志 | `$HOME/tmp/weupnp/logs/12-mvn-package-1.log` |
| 命令行覆盖无效（已排除方向）日志 | `$HOME/tmp/weupnp/logs/13-mvn-package-2.log` |
| 修复后构建成功日志 | `$HOME/tmp/weupnp/logs/14-mvn-package-3.log` |
| 上游 Main 实跑日志 | `$HOME/tmp/weupnp/logs/16-upstream-Main-run.log` |

---

## 五、测试环境

```
平台      : OpenHarmony (os.name=harmonyos, hongmeng kernel 1.12.0, aarch64)
JVM       : openjdk version "17.0.13" 2024-10-15 — OpenJDK Runtime Environment BiSheng (17.0.13+6)
            java.vendor=bisheng  java.vm.vendor=bisheng
构建工具  : Apache Maven 3.6.3 (cecedd343002696d0abb50b32b541b8a6ba2883f)
包引用    : weupnp/0.1.4@ohpcd/stable
profile   : ci/conan/profiles/ohos-aarch64
产物      : libexec/weupnp-0.1.4.jar (30372 B, sha256 23598fb74076e9ab7317727050f338111f5e6bb9c6e641419caf2788f2a17aed)
字节码    : Java 8 (major 52)
```

---

*报告生成时间: 2026-10-01*
