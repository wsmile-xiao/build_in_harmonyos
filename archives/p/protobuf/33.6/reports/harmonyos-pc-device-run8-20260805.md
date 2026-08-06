# protobuf 33.6 HarmonyOS PC 真机补测报告（run8）

## 测试环境

- 日期：2026-08-05
- 目标库：protobuf 33.6
- PR：#3202
- Issue：#1368
- 真机：`currentUser@10.62.224.229:2222`
- 探测结果：`HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Tue Apr 28 07:33:02 UTC 2026 aarch64 Toybox`
- 远端目录：`/storage/Users/currentUser/codex-tests/protobuf-33.6-20260805`

## 上传与完整性

- 上传方式：Windows `ssh.exe` 标准输入 + 远端 `/system/bin/dd`，未依赖 SFTP。
- 补测包：`protobuf-device-rebuilt-tests-20260805-33-6-v6.tar.gz`
- 本地 SHA256：`8D954C7920F2A136020C6FC19B5968FEA574CEB6FE7B7CED4ACB1A5B3E14BC6B`
- 远端 SHA256：`8d954c7920f2a136020c6fc19b5968fea574ceb6fe7b7ced4acb1a5b3e14bc6b`
- 执行前处理：测试 ELF 在最终 HMDFS 路径使用 `/data/service/hnp/bin/binary-sign-tool` 原地自签名，并恢复执行位。

## 测试结果

| 阶段 | 结果 |
|------|------|
| `lite-test` | 104/104 通过，rc=0 |
| `full-test` | 4521 项运行，4505 项通过、16 项上游 SKIPPED，rc=0 |
| `lazily-build-dependencies-test` | 9/9 通过，rc=0 |
| `upb-test` | 269/269 通过，rc=0 |
| `consumer-any` | 5 个断言通过，rc=0 |
| `consumer-serialize` | 5 个断言通过，rc=0 |
| `consumer-json` | 5 个断言通过，rc=0 |
| `consumer-arena` | 4 个断言通过，rc=0 |
| `protoc --version` | 输出 `libprotoc 33.6`，rc=0 |

总结果：`OVERALL_RC=0`，`device-run8.done=0`。

## 关键修复说明

- 旧版 Googletest 的 `CapturedStream` 在非 Android POSIX 分支硬编码 `/tmp/`，HarmonyOS PC 用户态环境中不可写；补丁改为在通用 POSIX 分支复用 `testing::TempDir()`，由配方注入 `TEST_TMPDIR`/`TMPDIR`，不引入平台条件宏。
- Protobuf 插件测试在 `--plugin=...=<裸文件名>` 形式下不能可靠按 `PATH` 解析插件；补丁使用通用 `ResolvePluginPathForTest()` 运行期解析表达式，按当前工作目录优先查找 `./<plugin>`，再查找 `./build/Release/<plugin>`，兼容 CI 构建目录和真机 staging 根目录。
- Windows-to-OHOS clean build 中，upb 生成链路使用 host `protoc`/host plugin 时，同步将 `add_custom_command()` 的生成依赖切到 host 可执行文件路径，并在 CMake 3.27+ 启用 `DEPENDS_EXPLICIT_ONLY`，避免 generated source 隐式依赖目标端 `protoc`/`libupb.a` 形成 Ninja dependency cycle。

## 证据摘录

```text
===== BEGIN lite-test =====
[==========] Running 104 tests from 8 test suites.
[==========] 104 tests from 8 test suites ran. (6 ms total)
[  PASSED  ] 104 tests.
===== END lite-test rc=0 =====
===== BEGIN full-test =====
[==========] Running 4521 tests from 265 test suites.
[==========] 4521 tests from 265 test suites ran. (42860 ms total)
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
