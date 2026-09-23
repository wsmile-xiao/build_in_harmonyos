# open62541 1.5.6 上游测试报告

## 执行结论

- 测试设备：HarmonyOS aarch64 真机 `10.62.229.155:2222`
- 测试方式：上游 CMake/CTest + Check 0.15.2，独立于生产 Conan recipe
- 源码测试清点：205 个 C 测试源文件，3521 个 `START_TEST` 用例
- CTest 注册：141 项，其中 140 个 Check 测试程序、1 个跨命名空间代码生成测试
- 最终结果：141/141 通过，0 失败，0 个已注册测试未执行
- Check 测试程序覆盖：140 个程序，3118 个源代码用例
- 未注册测试源文件：65 个，403 个源代码用例

首轮使用单项超时 120 秒，结果为 128/141 通过、13/141 超时。以下 13 项在同一
真机上使用单项超时 300 秒串行复测，结果为 13/13 通过：

```text
check_server_asyncop
check_services_subscriptions
check_server_readwrite
check_services_nodemanagement_callbacks
check_pubsub_publish
check_pubsub_subscribe
check_client
check_client_async_read
check_client_highlevel
check_client_highlevel_read
check_client_highlevel_write
check_client_highlevel_readwrite
check_client_subscriptions
```

因此首轮的 13 项是设备执行时间超过 120 秒，不是测试失败。上述两次结果合并后，
141 个已注册测试入口全部有实际执行结果。

## 未注册测试及原因

以下文件未被当前 OHOS CMake 配置注册为 CTest。括号内为该文件中的
`START_TEST` 用例数。

### 1. Linux-only 或平台能力限制

共 5 个文件、17 个用例。上游 CMake 只在 `CMAKE_SYSTEM_NAME=Linux` 且满足相应
条件时注册；其中 raw Ethernet 还需要 Linux raw socket 能力，network replay 还需要
Linux pcap 环境。HarmonyOS 本轮不伪造这些平台条件。

```text
tests/check_eventloop_eth.c (2)
tests/check_eventloop_interrupt.c (2)
tests/network_replay/check_network_replay.c (3)
tests/pubsub/check_pubsub_connection_ethernet.c (8)
tests/pubsub/check_pubsub_publish_ethernet.c (2)
```

### 2. 加密功能关闭

共 34 个文件、164 个用例。当前产品构建使用 `UA_ENABLE_ENCRYPTION=OFF`，因此
TLS/证书/安全策略/加密 PubSub 测试由上游 CMake 排除。`check_certificategroup_none.c`
是无加密构建也会注册的例外，已包含在 141 项 CTest 中，不计入下面清单。

```text
tests/client/check_client_authentication.c (8)
tests/client/check_client_encryption.c (1)
tests/encryption/check_ca_chain.c (1)
tests/encryption/check_cert_generation.c (1)
tests/encryption/check_cert_validation_client_response.c (1)
tests/encryption/check_certificategroup.c (6)
tests/encryption/check_crl_validation.c (3)
tests/encryption/check_crypto_coverage.c (37)
tests/encryption/check_csr_generation.c (7)
tests/encryption/check_ecc_config.c (8)
tests/encryption/check_encryption_aes128sha256rsaoaep.c (3)
tests/encryption/check_encryption_aes256sha256rsapss.c (3)
tests/encryption/check_encryption_basic128rsa15.c (3)
tests/encryption/check_encryption_basic256.c (3)
tests/encryption/check_encryption_basic256sha256.c (3)
tests/encryption/check_encryption_basic256sha256_with_config.c (1)
tests/encryption/check_encryption_ecc.c (8)
tests/encryption/check_encryption_eccnistp256.c (8)
tests/encryption/check_encryption_eccnistp256_aesgcm.c (6)
tests/encryption/check_encryption_eccnistp256_chachapoly.c (6)
tests/encryption/check_encryption_key_password.c (1)
tests/encryption/check_gds_informationmodel.c (9)
tests/encryption/check_pubsub_securitypolicy_crypto.c (3)
tests/encryption/check_securitypolicy_crypto.c (5)
tests/encryption/check_update_certificate.c (3)
tests/encryption/check_update_trustlist.c (6)
tests/encryption/check_username_connect_none.c (2)
tests/pubsub/check_pubsub_decryption.c (6)
tests/pubsub/check_pubsub_encryption.c (1)
tests/pubsub/check_pubsub_encryption_aes256.c (1)
tests/pubsub/check_pubsub_subscribe_encrypted.c (2)
tests/server/check_discovery.c (6)
tests/server/check_json_config_pki.c (1)
tests/server/check_server_getendpoints.c (1)
```

### 3. MQTT 未启用

共 3 个文件、10 个用例。当前 `UA_ENABLE_MQTT=OFF`；相关测试还需要独立 MQTT
broker，不能在本轮没有 broker 的真机窗口中注册执行。

```text
tests/check_eventloop_mqtt.c (1)
tests/pubsub/check_pubsub_connection_mqtt.c (7)
tests/pubsub/check_pubsub_mqtt.c (2)
```

### 4. Nodeset Loader 未启用

共 9 个文件、101 个用例。当前 `UA_ENABLE_NODESETLOADER=OFF`，上游 CMake 不添加
`tests/nodeset-loader` 子目录。

```text
tests/nodeset-loader/check_nodeset_loader_adi.c (2)
tests/nodeset-loader/check_nodeset_loader_autoid.c (2)
tests/nodeset-loader/check_nodeset_loader_compare_di.c (1)
tests/nodeset-loader/check_nodeset_loader_di.c (1)
tests/nodeset-loader/check_nodeset_loader_input.c (1)
tests/nodeset-loader/check_nodeset_loader_ordering_di.c (1)
tests/nodeset-loader/check_nodeset_loader_plc.c (2)
tests/nodeset-loader/check_nodeset_loader_testnodeset.c (10)
tests/nodeset-loader/check_nodeset_loader_ua_nodeset.c (81)
```

### 5. PubSub 文件配置未启用

共 1 个文件、3 个用例。当前 `UA_ENABLE_PUBSUB_FILE_CONFIG=OFF`。

```text
tests/pubsub/check_pubsub_configuration.c (3)
```

### 6. PubSub SKS 未启用

共 5 个文件、42 个用例。当前 `UA_ENABLE_PUBSUB_SKS=OFF`，且上游要求加密功能
同时启用。

```text
tests/pubsub/check_pubsub_sks_client.c (9)
tests/pubsub/check_pubsub_sks_keystorage.c (8)
tests/pubsub/check_pubsub_sks_pull.c (9)
tests/pubsub/check_pubsub_sks_push.c (6)
tests/pubsub/check_pubsub_sks_securitygroups.c (10)
```

### 7. Alarms and Conditions 未启用

共 1 个文件、46 个用例。当前 `UA_ENABLE_SUBSCRIPTIONS_ALARMS_CONDITIONS=OFF`。

```text
tests/server/check_server_alarmsconditions.c (46)
```

### 8. Full NS0 未启用

共 7 个文件、20 个用例。当前 `UA_NAMESPACE_ZERO=REDUCED`，这些 nodeset compiler
和 interfaces 测试要求 `UA_NAMESPACE_ZERO=FULL`。跨命名空间 Python 代码生成测试
不依赖 Full NS0，已作为第 141 项 CTest 执行并通过。

```text
tests/nodeset-compiler/check_client_get_remote_datatypes.c (1)
tests/nodeset-compiler/check_client_nsMapping.c (3)
tests/nodeset-compiler/check_nodeset_compiler_adi.c (2)
tests/nodeset-compiler/check_nodeset_compiler_autoid.c (2)
tests/nodeset-compiler/check_nodeset_compiler_plc.c (2)
tests/nodeset-compiler/check_nodeset_compiler_testnodeset.c (9)
tests/server/check_interfaces.c (1)
```

## 未纳入 205 个 C 文件统计的测试入口

- `UA_BUILD_FUZZING=OFF`：未构建 fuzz executable；fuzz target 不是 Check
  `START_TEST` 用例，需要单独的 fuzzing engine 和 corpus。
- `UA_BUILD_INTEROP_TESTS=OFF`：未构建跨 SDK 互操作测试；该入口需要独立的服务端、
  客户端和跨 SDK 运行环境，也不是 Check `START_TEST` 用例。
- `UA_ENABLE_UNIT_TESTS_MEMCHECK=OFF`：未使用 Valgrind/DrMemory 包装器；这不影响
  普通 CTest 的注册和执行结果。
- Windows 本机未执行 AArch64 ELF；目标程序已在 HarmonyOS 真机执行。

## 环境说明

设备 `/tmp` 为只读目录，Check 测试因此不能使用默认临时目录。本次测试仅在隔离 job
内将 `TMPDIR` 和 `TEMP` 指向可写目录，并对设备临时测试树补充了 Check 查找脚本、
空 subunit 静态库以及 ranlib 替代命令。上述措施没有写入 open62541 版本目录、
Conan 配方或仓库基础设施。
