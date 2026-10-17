# protobuf 33.6 HarmonyOS PC 真机补测报告（run10）

## 测试环境

- 日期：2026-08-06
- 目标库：protobuf 33.6
- PR：#3202
- Issue：#1368
- 当前提交：`fa58d34951c112d12514e938e88d47ca6747db8a`
- 真机：`currentUser@10.62.148.108:2222`
- 探测结果：`HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Tue Apr 28 07:33:02 UTC 2026 aarch64 Toybox`
- 远端目录：`/storage/Users/currentUser/codex-tests/protobuf-33.6-20260805`

## 上传与完整性

- 上传方式：Windows `ssh.exe` 标准输入 + 远端 `/system/bin/dd`，未依赖 SFTP/scp。
- 补测包：`protobuf-device-stage-20260805-33-6-v7.tar.gz`
- 补测包本地 SHA256：`B97243CE9CF4329E6162E8B1C3ABB1CAF683B2AB2350CBB9693AC2F6B2C145E2`
- 补测包远端 SHA256：`b97243ce9cf4329e6162e8b1c3abb1caf683b2ab2350cbb9693ac2f6b2c145e2`
- 远端完整日志：`device-run10-20260806.log`
- 远端完整日志 SHA256：`025cdacca32325a572014fdc4274d42f8e3e8546098bdefbcdc3e1fddc2788d2`
- 执行前处理：测试 ELF 在最终 HMDFS 路径使用 `/data/service/hnp/bin/binary-sign-tool` 原地自签名，并恢复执行位。

## 测试结果

| 阶段 | 结果 |
|------|------|
| `lite-test` | 104/104 通过，rc=0 |
| `full-test` | 4521 项运行，4505 项通过，16 项上游 SKIPPED，rc=0 |
| `lazily-build-dependencies-test` | 9/9 通过，rc=0 |
| `upb-test` | 269/269 通过，rc=0 |
| `consumer-any` | 5 个断言通过，rc=0 |
| `consumer-serialize` | 5 个断言通过，rc=0 |
| `consumer-json` | 5 个断言通过，rc=0 |
| `consumer-arena` | 4 个断言通过，rc=0 |
| `protoc --version` | 输出 `libprotoc 33.6`，rc=0 |

总结结果：`OVERALL_RC=0`。

## 证据摘录

```text
===== BEGIN lite-test =====
[==========] Running 104 tests from 8 test suites.
[  PASSED  ] 104 tests.
===== END lite-test rc=0 =====
===== BEGIN full-test =====
[==========] Running 4521 tests from 265 test suites.
[  PASSED  ] 4505 tests.
[  SKIPPED ] 16 tests, listed below:
===== END full-test rc=0 =====
===== BEGIN lazily-build-dependencies-test =====
[==========] Running 9 tests from 1 test suite.
[  PASSED  ] 9 tests.
===== END lazily-build-dependencies-test rc=0 =====
===== BEGIN upb-test =====
[==========] Running 269 tests from 49 test suites.
[  PASSED  ] 269 tests.
===== END upb-test rc=0 =====
protobuf any: 5 assertions passed
protobuf serialize: 5 assertions passed
protobuf json: 5 assertions passed
protobuf arena: 4 assertions passed
libprotoc 33.6
OVERALL_RC=0
```

## 结论

本次补测在 HarmonyOS PC 真机上完整执行了 Protobuf 33.6 的 4 个上游 CTest 入口、4 个 Conan 消费者 API 场景和 `protoc --version`，全部自然退出 0。`full-test` 中 16 项为上游框架主动 SKIPPED，不是执行失败。
