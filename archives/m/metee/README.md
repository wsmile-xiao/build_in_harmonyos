# metee 6.2.3 — HarmonyOS PC 适配说明

## 概况

`metee` 是 Intel **MEI（Management Engine Interface）** 库：通过 `/dev/mei*`
上的 `ioctl` 查找并访问 Intel 管理引擎设备（序列号、遥测、固件存储等）。

- 上游：https://github.com/intel/metee
- 形态：CMake 工程
- 产物：`lib/libmetee.a`、`include/metee.h`
- 依赖：无
- 许可证：Apache-2.0

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `linux.cmake` 以 `-Werror` 叠加 `-Wsign-conversion` 等严格告警 | OHOS clang 15 在 `src/linux/mei.c` 的 ioctl 结果转换上触发 → 补丁去掉 `-Werror`（保留 `-Wall` 及其余告警） |
| 2 | `IOCTL_MEI_CONNECT_CLIENT_VTAG` 探测 | `check_symbol_exists` 在 OHOS 头缺失时自动回退到随包 `src/linux/include` |
| 3 | 上游测试需 GoogleTest + 真实 MEI 设备 | `test_requires("gtest/1.17.0")` 提供 GoogleTest（绕开上游 ExternalProject 联网 clone），build() 中构建并运行上游套件；无 MEI 设备时上游 fixture `GTEST_SKIP()` |
| 4 | 2 个上游用例未遵循 no-device 约定 | 仅测试层补 skip 补丁（`PROD_N_TestGetMeiKind`、`PROD_MKHI_MoveSemantics`），有设备时行为不变 |

## 测试

### 上游

`BUILD_TEST=ON` 构建并运行上游 GoogleTest 套件：**36 个实例执行（3 PASSED + 33 SKIPPED，0 FAILED）**。无 Intel MEI 设备（`/dev/mei*`）时上游 fixture 调用 `GTEST_SKIP()`；GoogleTest 由制品仓 `gtest/1.17.0` 提供（`test_requires` + `GTest_DIR`）。

### 消费者测试（test_package）

`test_package/test_metee.c` 编译并运行一个程序调用 `TeeInit()`，断言返回
`TEE_DEVICE_NOT_FOUND`（测试环境无 MEI 设备），验证库可链接且 API 可调用。

## 已知限制

- 未在真实 Intel MEI 硬件上验证设备交互（CI 无该硬件）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
