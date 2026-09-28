## PR 信息

- **三方库名称**：periphery
- **上游版本**：2.5.0
- **上游仓库地址**：https://github.com/vsergeev/c-periphery
- **适配路径**：路径 A（基础适配，无补丁）
- **使用知识库**：openharmony-compile-agent（E330：OHOS 未知 CMake 平台的 SONAME/版本符号链接处理）

**版本偏差说明**：任务平台登记版本为 3.8.0，但 C 库 periphery 上游（vsergeev/c-periphery，原 hawkninja/periphery，该组织仓库已 404）最新正式 tag 为 **v2.5.0**（2025-11-02 发布），不存在 3.8.0；网上可查的 "periphery 3.8.0" 是 Swift 静态分析工具 peripheryapp/periphery，非 C 库（lang 不符，按 R47 只适配 C/C++）。故本 PR 适配 C 库实际最新版 **2.5.0**。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 套件 / 32 test 函数 / 721 断言 | 来源：上游 tests/ 目录（test_gpio/test_gpio_sysfs/test_i2c/test_led/test_mmio/test_pwm/test_serial/test_spi） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 上游无 ctest/pytest/make check 注册；上游 CI（.github/workflows/build.yml）只执行 `make all tests` + `cmake .. && make`（编译测试程序，从不运行） |
| **合计** | **8 套件 / 32 test 函数** | 全部硬件依赖型 |

**上游测试硬件依赖明细**（与上游 CI 不运行测试的原因一致）：

| 测试程序 | 依赖硬件 | 依赖设备 |
|---|---|---|
| test_gpio | GPIO 芯片 + 回环接线 | /dev/gpiochipN |
| test_gpio_sysfs | sysfs GPIO export | /sys/class/gpio（可写） |
| test_i2c | I2C 总线 + 0x51 EEPROM (24XX32) | /dev/i2c-N |
| test_led | 命名 LED | /sys/class/leds/<name> |
| test_mmio | **假设 BeagleBone Black (AM335x)**，直接读写物理地址 0x44e10000 (CONTROL_MODULE_BASE) 与 0x44e3e000 (RTCSS_BASE) | /dev/mem |
| test_pwm | PWM 芯片 + 回环接线 | /dev/pwmchipN |
| test_serial | 串口自环 | /dev/ttyS* |
| test_spi | SPI 总线 + 回环接线 | /dev/spidevN.M |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 8 套件（编译）+ 29 项消费者检查 | 编译口径一致 / +29 | 上游 8 套件按上游 CI 同口径编译验证 8/8 通过；消费者用例 29 项检查覆盖全部 7 模块 + version API |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 29 | +29 | test_package 消费者用例：模拟库使用者调用全部公开 API（new/close/free 往返 + 无效参数/不存在设备的约定错误码），无硬件依赖，aarch64-linux-ohos 交叉编译并运行 |
| **合计** | **8 套件 + 29 项** | **+29** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（源码零改动，无补丁）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游测试全部为硬件依赖型，在 HarmonyOS PC（无对应外设）上技术上不可运行，适配后补全了消费者视角的 API 可用性测试

- **补全的测试范围**：为全部 7 个模块（gpio/i2c/led/mmio/pwm/serial/spi）+ version 新增 29 项消费者检查，模拟业务上层组件作为"库的使用者"调用库对外公开 API，验证编译、链接、调用、错误码返回全部跑通
- **补全原因**：上游 32 个 test 函数全部需要真实外设硬件（GPIO 回环/I2C EEPROM/PWM/SPI 回环/串口自环/物理 MMIO，test_mmio 明确假设 BeagleBone Black）；本机实测设备面：/dev/i2c-*、/dev/spidev*、/dev/pwmchip*、/dev/ttyS*、/dev/mem 均不存在，/dev/gpiochip0-11 存在但 open 返回 EACCES（普通用户无 GPIO 设备权限），/sys/class/gpio EACCES —— 与上游自身 CI 只编译不运行测试的原因一致。8 套件的运行日志证据见 reports/upstream-test-run/
- **新增测试文件清单**：
  1. `test_package/test.c` — 29 项检查：periphery_version()/periphery_version_info() 版本 API + 7 模块 new/open(无效参数→ARG 错误码)/open(不存在设备→OPEN 错误码 + errno)/close/free 全链路
  2. `test_package/CMakeLists.txt` — 消费者工程（find_package(periphery) 经 CMakeDeps 链接）
  3. `test_package/MANIFEST.yml` — 测试说明（含与上游测试口径对照）

## 验证结果

- 编译状态：通过（本地 W3 本地 CI 模拟 conan create，clang 15 交叉编译 aarch64-linux-ohos，100% 通过，Pass rate 100.0% (1/1)）
- 上游测试用例通过率：编译验证 8/8（100%，与上游 CI 口径一致）；硬件运行类 32/32 test 函数在 PC 平台不可运行（无对应外设硬件 + GPIO 设备权限 EACCES），逐项原因见上表及 reports/upstream-test-run/*.log
- 新增测试用例通过率：29/29（100%）

## 补充说明

- 依赖：无 conan 外部依赖（仅系统 libc/libpthread）
- 共享库 SONAME：OHOS 为 CMake 未知平台，默认不处理 SONAME/版本符号链接（CI L5a/L5c 会失败）；按知识库 E330 方案注入 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`，产物为单一实体 libperiphery.so，DT_SONAME=libperiphery.so（相对名可重定位），生成 cmake 配置无 IMPORTED_NO_SONAME
- 源码 URL：codeload.github.com 为 GitHub 官方归档 CDN（与 github.com/archive/refs/tags/v2.5.0.tar.gz 同内容，sha256 065d304d... 全等；本仓库既有惯例，见 afsctool/parson/papirus-icon 等配方）
- 库功能说明：GPIO/I2C/SPI/PWM/Serial/MMIO/LED 的实际读写需要目标设备具备对应内核驱动与设备节点；在无外设的 PC 上各 open 按约定返回错误码，属预期行为而非适配缺陷
- 分支名：feat/periphery-2.5.0（前缀/库名-版本号）
