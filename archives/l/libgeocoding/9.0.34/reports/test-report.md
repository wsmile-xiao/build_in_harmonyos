# Test Report — libgeocoding 9.0.34

- 验证日期：2026-09-21
- 平台：HarmonyOS PC aarch64（本机**原生**执行，非交叉编译）
- profile：`ci/conan/profiles/ohos-aarch64`（`-pr:b` 与 `-pr:h` 同）
- 验证命令：`conan create archives/l/libgeocoding/9.0.34 -pr:b=ci/conan/profiles/ohos-aarch64 -pr:h=ci/conan/profiles/ohos-aarch64`
- 退出码：**0**（日志 `reports/logs/conan-create-20260921-0205.log`）

## 1. 上游测试（实际执行，非 test_package 替代）

| 套件 | 命令 | 执行 | 通过 | 失败 | 跳过 |
|---|---|---|---|---|---|
| `libphonenumber_test`（16 suites） | `./libphonenumber_test` | 327 | 327 | 0 | 0 |
| `generate_geocoding_data_test`（上游 `tests` 目标成员） | `./tools/generate_geocoding_data_test` | 2 | 2 | 0 | 0 |
| **合计** |  | **329** | **329** | **0** | **0** |

逐条用例名称与状态：`reports/upstream-tests.md`（329 条，全 PASSED）。

交叉核对（防漏测）：上游 `cpp/test/phonenumbers/**/*_test.cc` 静态 `TEST/TEST_F/TEST_P` 宏计数
= 327，`tools/cpp/test/cpp-build/generate_geocoding_data_test.cc` = 2，合计 **329 = 实际执行数**。

上游示例程序（`cpp/test/phonenumbers/geocoding/geocoding_test_program.cc`）：

```
$ ./geocoding_test_program
Mountain View, CA
$ echo $?
0
```

机器可读标记（build 内双通道打印 + 随包持久化到 `res/upstream_test_result.json`）：

```json
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "gtest",
 "command": "./libphonenumber_test + ./tools/generate_geocoding_data_test",
 "discovered": 329, "executed": 329, "passed": 329, "failed": 0, "skipped": 0,
 "suites": [{"name": "libphonenumber_test", "exit_code": 0, "ran": 327, "passed": 327, "failed": 0, "skipped": 0},
            {"name": "generate_geocoding_data_test", "exit_code": 0, "ran": 2, "passed": 2, "failed": 0, "skipped": 0}],
 "sample": {"name": "geocoding_test_program", "exit_code": 0, "output": "Mountain View, CA"}}
```

## 2. test_package（L1 消费者测试，独立于上游统计）

只使用已安装包的公开头 + conan 提供的编译/链接参数（不做缺失库兜底）：

| # | 用例 | 结果 |
|---|---|---|
| 1 | `parse-us-number` | OK |
| 2 | `validate-us-number` | OK |
| 3 | `geocode-us-en`（`Mountain View, CA`） | OK |
| 4 | `geocode-cn-zh`（`北京市`，ICU i18n 本地化路径） | OK |
| 5 | `geocode-de-de`（`Berlin`） | OK |
| 6 | `ohos-concurrent-geocoding-embedded-data`（**HarmonyOS 专有**：8 线程并发 geocoder，覆盖本适配修复的 `absl::Mutex` 加锁路径；编译期嵌入数据、无外部文件/locale 依赖） | OK |

```json
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 6, "passedCount": 6,
 "ohos_specific_case": "ohos-concurrent-geocoding-embedded-data"}
```

## 3. 产物基线

```
lib/libgeocoding.a      16 370 142 B
lib/libphonenumber.a     1 147 820 B
include/phonenumbers/**（含 geocoding/）
licenses/LICENSE
res/upstream_test_result.json, res/upstream_test_cases.txt
```

## 4. 失败与修复轨迹（详见 notes.md）

| # | 失败 | 根因 | 修复 | 重验 |
|---|---|---|---|---|
| 1 | `MutexLock 弃用 [-Werror]` | abseil 20260107.1 弃用 `MutexLock(ptr)` × 上游 `-Wall -Werror` | 改非弃用构造（2 处，目标库源码） | 编译通过 |
| 2 | `undefined symbol: icudt78_dat / absl::log_internal / utf8_range_IsValid` | 静态归档不传递依赖，上游只发现 4 个目标 | `patches/0001` 追加 Conan 静态闭包 | 链接通过 |
| 3 | FetchContent 拉 GitHub / `can't locate protoc` | Conan 不写 `CMAKE_PREFIX_PATH`；protoc 不在系统 PATH | 显式设 `absl_DIR`、`CMAKE_PROGRAM_PATH` | configure 通过 |
| 4 | `test_metadata.cc: no such file` | Makefile 生成器 `.DELETE_ON_ERROR` × 上游空 `echo` 自定义命令 | 改用 Ninja 生成器 | 95/95 构建成功 |
| 5 | 逐条清单缺 1 条 | `TestFindAndConsume` 结果标记非行首 | 解析改 `re.search` | 329/329 完整 |

## 5. 结论

**上游测试 329/329 通过（失败 0 / 跳过 0），上游示例程序通过，test_package 6/6 通过
（含 1 项 HarmonyOS 专有用例），`conan create` exit 0。**
