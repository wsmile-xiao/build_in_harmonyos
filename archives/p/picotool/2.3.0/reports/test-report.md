# picotool 2.3.0 测试报告

- 测试日期: 2026-09-21
- 平台: HarmonyOS PC aarch64（ohos-aarch64 profile，clang 15）
- 验证方式: `conan create`（本地 W3 与 CI 同源同 profile）

## 一、上游测试清点（R51 三步法·第一步）

解压上游源码包 picotool-2.3.0.tar.gz（sha256 97aaf368...）全量检索：

- **无单元测试套件**：无 tests/ 目录；CMakeLists.txt 无 enable_testing/add_test；无 ctest/pytest 注册
- 上游实际验证 = `.github/workflows/test.yml`（无硬件冒烟）+ `bdev_test.sh`（需真机）
- 清点证据：test_package/MANIFEST.yml（逐 step 列出）

## 二、测试执行对比（R51 三步法·第二步）

| # | 上游测试（.github/workflows/test.yml） | 适配后执行（test_package） | 结果 |
|---|---|---|---|
| 1 | Test step: `picotool help` | `picotool help` | PASS |
| 2 | Test step: `picotool info -a blink.uf2` | `picotool info -a blink.uf2`（官方 blink_universal.uf2） | PASS |
| 3 | Test step: `picotool info -a hello_world.uf2` | `picotool info -a hello_world.uf2`（官方 hello_universal.uf2） | PASS |
| 4 | Test step: `picotool info -a flash_nuke.uf2` | `picotool info -a flash_nuke.uf2`（官方 nuke_universal.uf2） | PASS |
| 5 | Test libusb compiled: `picotool help load` | `picotool help load` | PASS |
| 6 | Test libusb compiled: `picotool help save` | `picotool help save` | PASS |
| 7 | Test libusb compiled: `picotool help erase` | `picotool help erase` | PASS |
| 8 | test-older-sdk job: `picotool version <sdk>` 版本断言 | `picotool version` + `picotool version 2.3.0` | PASS |
| 9 | bdev_test.sh（分区表/bdev 端到端） | SKIP | SKIP |
| 10 | test-examples job（构建 pico-examples） | SKIP | SKIP |
| 11 | （补充）消费者测试 test.c | test_picotool（bin/picotool 有效 64 位 ELF） | PASS |

### SKIP 用例具体技术原因（R51 要求逐项说明）

- **#9 bdev_test.sh**：脚本通过 picoboot USB 协议对真实 RP2040/RP2350 设备执行
  erase/reboot/load/info（脚本第 22-31 行），CI 环境无 Pico 硬件，无法复现。
- **#10 test-examples job**：需 arm-none-eabi 交叉工具链构建 pico-examples 固件仓库，
  验证对象是 pico-examples 的可构建性而非 picotool 自身功能，且本机无 bare-metal
  ARM 工具链（CI 能力矩阵：无 arm-none-eabi）。

## 三、通过率

- **CI 环境可复现用例：9/9 = 100%**（#1-8 上游同款 + #11 消费者测试）
- SKIP：2 项（硬件/交叉工具链依赖，原因如上）
- CI 门禁：L0 结构 PASS / L1 test_package 执行 PASS / L1e 破坏性负向验证 PASS
  （移走 bin/lib 后测试失败，证明测试真实依赖被测包，R34）/ L4 补丁安全 PASS /
  L5 产物基线 PASS / L2 smoke skip（picotool 为子命令风格 CLI，无 `--version` 长选项，
  L2 通用检查不适用，非阻塞）
- 本地 W3：`.ci-result.json` exit_code=0（finish 自动写入）

## 四、执行环境

- conan 2.29.1（OHOS 适配版），remote ohpcd（libusb/1.0.27 已发布，conan download 实测）
- pico-sdk 2.3.0 官方配套版本 vendor（PICO_SDK_PATH 方式）
- UF2 固件来源：github.com/raspberrypi/pico-sdk-prebuilts releases（上游 CI 同源）
