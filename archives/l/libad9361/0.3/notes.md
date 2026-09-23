# libad9361 0.3 — HarmonyOS PC 适配说明

## 概况

libad9361 是 Analog Devices AD9361/AD9364 RF 收发器的辅助库：RF 时钟链计算、FIR 滤波器
设计（remez）、基带自动速率、多芯片同步、FMComms5 相位同步。通过 libiio 访问芯片。

- 上游：https://github.com/analogdevicesinc/libad9361-iio （tag `v0.3`）
- 形态：C 共享库 + 头文件 `ad9361.h`
- 依赖：`libiio/0.25`（制品仓已发布）
- 许可证：LGPL-2.1-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 依赖 libiio | `requires("libiio/0.25")`；`package_info().requires=["libiio::libiio"]` 传播 |
| 2 | 上游用 `find_library(iio)`/`find_path(iio.h)` | 直接注入缓存变量 `LIBIIO_INCLUDEDIR`/`LIBIIO_LIBRARIES`，find_* 命中缓存即跳过搜索 |
| 3 | `cmake_minimum_required(2.8.12)` | 新 CMake 拒绝 → `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | `_GNU_SOURCE` 仅对 Linux 定义 | OHOS 的 `CMAKE_SYSTEM_NAME=HarmonyOS` → 显式 `-D_GNU_SOURCE=1` |
| 5 | 上游测试需硬件 | 只有 `FilterDesignerTest`/`GenerateRatesTest` 是纯计算；另 3 个需真实 AD936x，未运行 |
| 6 | 测试运行库路径 | 测试链接共享 libad9361/libiio → 运行前把构建目录与 libiio/lib 加入 `LD_LIBRARY_PATH`，并在源 `test/` 目录运行以读取 `*.taps` |

## 测试

### 上游

`test/CMakeLists.txt` 注册 **5** 个测试：

- `FilterDesignerTest`（纯计算）：对各速率设计 RX/TX FIR，与随包 `rateRX_*.taps`/`rateTX_*.taps`
  参考比对（容差 ±2）；`build()` 运行并通过。
- `GenerateRatesTest`（纯计算）：从 5.2 到 61.44 MSPS 逐点对比
  `ad9361_calculate_rf_clock_chain` 与参考实现；`build()` 运行并通过。
- `FilterDesignerHardwareTest`、`AutoRateTest`、`FMComms5SyncTest`：需要真实 AD936x（经 libiio），未运行。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_libad9361.c` 共 **11** 条断言：

- `ad9361_calculate_rf_clock_chain(5208334)` 返回 0；RX/TX 共享正 BBPLL；
  RX ADC 时钟在 [25MHz,640MHz]；RX/TX 时钟链非递增；>61.44MSPS 被拒绝
- `ad9361_calculate_rf_clock_chain_fdp(1000000)`：返回 0，RX/TX `Rdata>0`，RX `FIR∈[1,4]`
- `ad9361_generate_fir_taps`（RX）：返回 0 且 tap 数合理

## 已知限制

- 需要硬件的功能（多芯片同步、auto-rate、FMComms5 相位同步、写 FIR 到设备）未验证。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
