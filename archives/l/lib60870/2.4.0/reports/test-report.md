# lib60870 2.4.0 测试报告（HarmonyOS PC / aarch64）

## 测试环境
- 设备: HarmonyOS PC（本机原生），HongMeng Kernel 1.12.0 aarch64
- 编译器: clang 15.0.4（OHOS SDK），musl libc
- Conan: 2.29.1（OHOS 适配版），profile ohos-aarch64（os=OHOS, arch=armv8）
- 源码: https://github.com/mz-automation/lib60870/archive/refs/tags/v2.4.0.tar.gz（sha256 5c4b9bded9555e914a1adcaaebbea3631828a6b08bd6d21573a62f34d439ea82）

## 上游测试套件（真实执行）

上游测试框架：Unity（vendored `tests/unity/`），单二进制 `tests/tests`（`tests/all_tests.c`，9633 行，`RUN_TEST` 121 个）。

- **121 个 RUN_TEST 中 31 个被 `#if (CONFIG_CS104_SUPPORT_TLS == 1)` 包裹**：TLS 用例（test_CS104_MasterSlave_TLS*），仅当 vendored mbedtls 存在且 `-DCONFIG_CS104_SUPPORT_TLS=1` 时编译。本包未启用 TLS（上游 dependencies/ 目录需手动放置 mbedtls 2.28/3.6 源码，非构建必需依赖），因此实际编译并执行的用例为 **90 个**——与上游在无 TLS 配置下的行为完全一致（上游 CI matrix 的 no-TLS job 同样跳过这 31 个）。
- **执行方式**：`conan create` 的 `build()` 内，`can_run(self)` 为真（本机可运行 OHOS 二进制）时构建 tests 目标并以 `conanrun` env 运行 `tests/tests`（测试二进制静态链接 lib60870，无外部共享库依赖）。
- **执行次数**：shared 与 static 两次 conan create 均真实执行。

### 执行结果（shared 模式，2026-09-14）

```
-----------------------
90 Tests 0 Failures 0 Ignored
OK
```

exit code 0。逐用例全部 `:PASS`（90 行 PASS、0 行 FAIL、0 行 IGNORE）。

### 执行结果（static 模式，2026-09-14）

```
-----------------------
90 Tests 0 Failures 0 Ignored
OK
```

### 用例分布（90 个非 TLS 用例）

| 类别 | 数量 | 代表用例 |
|------|------|----------|
| 版本/基础 | 1 | test_version_number |
| CP56Time2a/CP24Time2a 时间 | 4 | test_CP56Time2a, test_CP56Time2aToMsTimestamp |
| 信息对象编解码（M_SP/M_DP/M_ST/M_ME/M_IT 等） | 41 | test_SinglePointInformation, test_MeasuredValueScaled |
| 命令与设置点（C_SC/C_DC/C_RC/C_SE） | 14 | test_SingleCommand, test_SetpointCommandScaled |
| 文件服务/日志 | 3 | test_FileDirectory, test_QueryLog |
| CS104 主从交互/事件队列/冗余组 | 17 | test_CS104SlaveEventQueueOverflow, test_CS104_Connection_StartDTTimeout |
| CS101 ASDU 边界 | 2 | test_CS101_ASDU_addObjectOfWrongType |
| 其他（IP 地址、转换） | 8 | test_IpAddressHandling, test_ScaledNormalizedConversion |

（31 个 TLS 用例未编译：TLS 支持未启用，见上）

## 消费者测试（test_package）

- test.c 真实调用包公开 API：Lib60870_getLibraryVersionInfo、CS101_ASDU_create/addInformationObject/getTypeID/getNumberOfElements/getCOT/getElement、SinglePointInformation/StepPositionInformation 全套、CP56Time2a_createFromMsTimestamp + Hal_getTimeInMs、CS104_Slave_create/setServerMode/getConnectionParameters/destroy
- 断言数：20（版本 3 + ASDU 路径 8 + CP56Time2a 1 + CS104 Slave 3 + StepPosition 3 + 空指针/错误路径 2）
- 结果：**PASS（exit 0）**，shared 与 static 两种模式均通过

```
lib60870 consumer test: PASS (version 2.4.0, ASDU population, CP56Time2a, CS104 slave cycle, step position)
```

## conan create 汇总

| 模式 | 包 ID | 结果 |
|------|-------|------|
| shared=True（默认） | 01d92cf349a0dd98ff915f4bd99a04430171517f | ✅ created，上游 90/90 + 消费者 PASS |
| shared=False | 21b17f8b2bc0e9511e276e3d57a23893067cefe5 | ✅ created，上游 90/90 + 消费者 PASS |

## 结论

- 上游测试通过率：90/90 = **100%**（可执行范围内；31 个 TLS 用例因 TLS 未启用不编译，属上游既定行为）
- 消费者测试通过率：1/1 = 100%
- 本地 conan create 全绿，可提交 CI
