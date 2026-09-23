# metee 6.2.3 — HarmonyOS PC 适配说明

## 概况

`metee` 是 Intel MEI（Management Engine Interface）库，通过 `/dev/mei*` 的 ioctl
访问 Intel 管理引擎设备。产物为 `libmetee.a` 与 `metee.h`。

- 上游：https://github.com/intel/metee
- 形态：CMake
- 依赖：无
- 许可证：Apache-2.0

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `-Wall -Werror` + `-Wsign-conversion` | OHOS clang 15 在 `mei.c` 的 ioctl 转换上触发 → 去 `-Werror`（保留其余告警） |
| 2 | 缺 `IOCTL_MEI_CONNECT_CLIENT_VTAG` | 自动回退到随包 `src/linux/include` |
| 3 | 上游测试需 GoogleTest + 真实设备 | `test_requires("gtest/1.17.0")` + `GTest_DIR`；build() 中运行上游套件，无设备时 `GTEST_SKIP()` |
| 4 | 2 个用例未遵循 no-device 约定 | 仅测试层 skip 补丁（`_patch_tests`） |

## 测试

### 上游

`BUILD_TEST=ON` 运行上游 GoogleTest：**36 实例（3 PASSED + 33 SKIPPED，0 FAILED）**；无 MEI 设备时 fixture `GTEST_SKIP()`。

### 消费者测试（test_package）

`test_package/test_metee.c`：调用 `TeeInit()`，断言 `TEE_DEVICE_NOT_FOUND`。

## 已知限制

- 未在真实 MEI 硬件上验证。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
