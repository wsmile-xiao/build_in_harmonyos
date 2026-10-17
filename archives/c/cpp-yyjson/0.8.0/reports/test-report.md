# Test Report — cpp-yyjson 0.8.0

**Date**: 2026-09-22
**Platform**: HarmonyOS PC (aarch64-linux-ohos), OHOS SDK LLVM 15 (clang 15.0.4)
**Profile**: ci/conan/profiles/ohos-aarch64

## 上游测试（Upstream tests）

Source: `test/test.cpp`（GTest，`gtest_discover_tests(PRE_TEST)` 注册）
Executable: `cpp_yyjson_test`

| 套件 | 用例数 | 结果 |
|------|--------|------|
| Writer | 11 | 11/11 通过 |
| Reader | 9 | 9/9 通过 |
| Readme | 1 | 1/1 通过 |
| **合计** | **21** | **21/21 (100%)** |

命令：`conan create archives/c/cpp-yyjson/0.8.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`（recipe build() 内实际运行 `cpp_yyjson_test`）

日志：`reports/conan-create.log`（SHA256: 见 `.ci-result.json` log_sha256 / `sha256sum` 追溯）

## 双口径统计

- `source_declared_total`：21（test/test.cpp 中 21 个独立 `TEST()` 用例；bench_read/bench_write 为基准程序非断言用例，`CPPYYJSON_BUILD_BENCH=OFF` 不实例化）
- `configured_executable_total`：1（cpp_yyjson_test，GTest 21 项注册）
- `executed_passed_total`：21
- 失败数：0；未运行/未实例化数：benchmark 2 个（不属上游测试用例，按任务规则不计入独立用例）
- 通过率：21/21 (100%)；当前配置可执行集合通过率同为 21/21 (100%)

## test_package 消费者验证（Conan L1）

| 用例 | 内容 | 结果 |
|------|------|------|
| test_cpp-yyjson | 仅通过公开头文件调用 read/as_object/as_int/write 等公开 API，验证编译/链接/运行 | Passed |
| test_ohos_special | HarmonyOS 专项：JSON 往返、容器转换、字段反射（VISITABLE_STRUCT），验证 OHOS libc++15 能力守卫回退路径 | Passed |

`ctest`: 2/2 tests passed。

## 适配说明

- header-only CMake INTERFACE 库，无 bin 产物，无需 commands.json（R38）
- SDK libc++15 缺失 `<source_location>`/`<format>`/ranges 算法，以 3 个 portability 补丁适配（`__has_include`/`__cpp_lib_format` 守卫，无平台宏）
- 上游测试笔误修正：`test.cpp` `cast<X>(serialized)` → `cast<X>(serialized5)`（反射往返用例原本无法通过）

## 验证命令摘要

```bash
python3 scripts/ohc-run.py conan-verify cpp-yyjson 0.8.0   # G1-G4 全 PASS
# 上游：21/21 PASSED；test_package ctest：2/2 passed
```