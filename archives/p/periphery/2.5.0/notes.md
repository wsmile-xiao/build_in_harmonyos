# periphery 2.5.0 适配笔记

## 任务说明

- 任务来源：智能任务平台 contrib-13897（periphery，lang=c，claimer=Joy777666）
- **版本偏差说明**：任务平台登记版本为 3.8.0，但上游 C 库 periphery（github.com/vsergeev/c-periphery，
  原 hawkninja/periphery，hawkninja 组织仓库已不存在）最新正式 tag 为 **v2.5.0**（2025-11-02 发布），
  不存在 3.8.0；网上可查到的 "periphery 3.8.0" 为 Swift 静态分析工具（peripheryapp/periphery），
  非 C 库，与本任务 lang=c 不符。按 R47 只适配 C/C++ 库，故本 PR 适配上游 C 库最新版 **2.5.0**。
- 上游源码: https://github.com/vsergeev/c-periphery/archive/refs/tags/v2.5.0.tar.gz

## 编译环境
- 构建系统: CMake（上游同时提供 Makefile，二者等价；配方采用 CMake 主构建路径）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK 工具链，aarch64-linux-ohos）
- 状态: built（本笔记随 conan-verify/finish 结果更新）

## 编译步骤

原生（主机同架构 aarch64，用于上游测试运行）：
```bash
CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar make all tests
# 8 个测试程序全部编译通过（PERIPHERY_GPIO_CDEV_SUPPORT=1，主机内核头含 linux/gpio.h V1）
```

交叉（OHOS aarch64，Conan 配方路径）：
```bash
conan create archives/p/periphery/2.5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CMakeToolchain 自动设置 CMAKE_SYSTEM_NAME=HarmonyOS；check_source_compiles/check_symbol_exists
# 在 OHOS SDK 内核头下探测 GPIO cdev 支持并据此定义 PERIPHERY_GPIO_CDEV_SUPPORT
```

## 上游测试用例清点（R51 三步法）

**Step 1 清点**：上游 tests/ 目录 8 个测试源文件（test_gpio / test_gpio_sysfs / test_i2c / test_led /
test_mmio / test_pwm / test_serial / test_spi），共 32 个 test 函数、721 个 passert 断言。
无 ctest/pytest/make check 注册——上游 CI（.github/workflows/build.yml）只做
`make all tests` + `cmake .. && make` **编译测试程序，从不运行**，因为测试全部依赖真实硬件：

| 测试程序 | 依赖硬件 | 依赖设备路径 |
|---|---|---|
| test_gpio | GPIO 芯片 + 回环接线 | /dev/gpiochipN + 两个回环 GPIO |
| test_gpio_sysfs | sysfs GPIO export | /sys/class/gpio（可写） |
| test_i2c | I2C 总线 + 0x51 EEPROM (24XX32) | /dev/i2c-N |
| test_led | 命名 LED 回环 | /sys/class/leds/<name> |
| test_mmio | **假设 BeagleBone Black (AM335x)**，直接读写物理地址 0x44e10000 (CONTROL_MODULE_BASE) 与 0x44e3e000 (RTCSS_BASE) | /dev/mem |
| test_pwm | PWM 芯片 + 回环接线 | /dev/pwmchipN |
| test_serial | 串口自环 | /dev/ttyS* |
| test_spi | SPI 总线 + 回环接线 | /dev/spidevN.M |

**Step 2 实际运行**：在 HarmonyOS PC aarch64 真机（与本任务目标平台同架构）原生编译后逐个运行
（完整日志见 reports/upstream-test-run/ 目录）：

| 测试程序 | 运行命令 | 结果 | 失败原因（具体技术原因） |
|---|---|---|---|
| test_gpio | `test_gpio /dev/gpiochip0 55 57` | 断言失败 exit=134 (test_open_config_close:59) | /dev/gpiochip0 open 返回 EACCES（普通用户无 GPIO 字符设备权限，SELinux/设备权限限制），无法 request GPIO 线 |
| test_gpio_sysfs | `test_gpio_sysfs 55 57` | 断言失败 exit=134 (test_open_config_close:54) | /sys/class/gpio 目录 EACCES，export 文件不可写，sysfs GPIO 通路不可用 |
| test_i2c | `test_i2c /dev/i2c-1` | 断言失败 exit=134 (test_open_config_close:43) | PC 设备面不存在 /dev/i2c-* 节点（无 I2C 控制器驱动暴露用户态设备），且需 0x51 EEPROM 硬件 |
| test_led | `test_led user-led0` | 断言失败 exit=134 (test_open_config_close:43) | PC 无 /sys/class/leds 命名 LED 资源 |
| test_mmio | `test_mmio` | 断言失败 exit=134 (test_open_config_close:43) | 测试硬编码 BeagleBone Black 物理地址 0x4804C000 且需 /dev/mem（PC 无此设备）；上游 README 明示该套件仅假设 BBB 主机 |
| test_pwm | `test_pwm /dev/pwmchip0 0` | 断言失败 exit=134 (test_open_config_close:52) | PC 设备面无 /dev/pwmchip* 节点 |
| test_serial | `test_serial /dev/ttyS0` | 断言失败 exit=134 (test_open_config_close:62) | PC 设备面无 /dev/ttyS* 节点（仅 tty0/ttyHW* 显示终端） |
| test_spi | `test_spi /dev/spidev0.0` | 断言失败 exit=134 (test_open_config_close:47) | PC 设备面无 /dev/spidev* 节点 |

设备面证据（probe 程序，本机实测）：/dev/gpiochip0-11 存在但 open EACCES；
/dev/i2c-*、/dev/spidev*、/dev/pwmchip*、/dev/ttyS*、/dev/mem 均 ENOENT；/sys/class/gpio EACCES。

**结论**：上游 32 个 test 函数全部依赖真实外设硬件（GPIO 回环/I2C EEPROM/PWM/SPI 回环/
串口自环/物理 MMIO），在 HarmonyOS PC（无上述外设且设备权限受限）上**技术上不可运行**——
这与上游自身 CI 的做法一致（上游 CI 仅编译测试不运行）。本机验证等价执行了上游 CI 的
完整编译动作：8/8 测试程序 + 库编译 100% 通过（clang 15，-Wall -Wextra -pedantic 零错误，
仅 1 个无害 warning：-Wno-stringop-truncation 为 GCC 专用选项，clang 忽略并提示等价选项，
属上游对 clang 的已知兼容告警）。

**上游测试用例通过率：编译验证 8/8 套件 100%（与上游 CI 口径一致）；硬件运行类
32/32 test 函数在 PC 平台不可运行（无对应外设硬件 + 设备权限 EACCES），原因逐项列于上表。**

**Step 3 适配后补全**：上游测试为硬件依赖型，本机无法运行，故 test_package 消费者用例
以"库使用者"视角验证可用性：调用全部 7 个模块（gpio/i2c/led/mmio/pwm/serial/spi）的
new/close/free 公开 API + version API，验证编译/链接/调用/错误码返回路径全部跑通（不依赖外设
存在，对无效设备的 open 返回约定错误码即验证了库的正确行为）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游仓库 hawkninja/periphery 404 | 作者迁移至 vsergeev/c-periphery | conandata.yml 指向 vsergeev/c-periphery v2.5.0 官方 tag 归档 |
| 2 | 任务版本 3.8.0 不存在于 C 库上游 | 任务登记把 Swift 同名工具 peripheryapp/periphery 3.8.0 误录为 C 库 | 适配 C 库实际最新版 2.5.0，PR 与 result 中如实说明 |
| 3 | 上游测试依赖真实硬件 | 测试套件设计为开发板（BBB/RPi）回环实验 | 等价执行上游 CI 的编译口径（8/8 通过）+ test_package 消费者用例验证 API 可用性 |

## 依赖版本

运行依赖：无（仅系统 libc/libpthread/libm，libpthread 由系统提供）
构建依赖：无 conan requires

## 验证结果

```bash
# 1. 上游测试编译（等价上游 CI build.yml）
make all tests  # 8/8 测试程序 + periphery.a 编译通过

# 2. 消费者用例（test_package，conan create 内执行）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 消费者程序编译链接通过并运行，打印 periphery_version() 与 7 模块 API 探测结果
```

## 注意事项

- 库功能（GPIO/I2C/SPI/PWM/Serial/MMIO/LED）需要目标设备具备对应内核驱动与设备节点，
  本 PR 只验证库本身的编译/链接/调用正确性；PC 上无外设时各 open 按约定返回错误码，属预期行为。
- CMake 探测 GPIO cdev 支持依赖目标内核头（linux/gpio.h），OHOS SDK 头下探测结果
  （V1/V2/0）由 CMake configure 阶段自动决定，无需硬编码。
- 共享库 SONAME 为 libperiphery.so.2.5（SOVERSION 2.5），与系统库无同名冲突（R26 不适用）。
---

**编译结束**: 2026-09-27 11:56
**最终状态**: built
