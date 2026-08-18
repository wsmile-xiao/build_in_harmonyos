# stlink 1.8.0 功能测试报告

**日期**: 2026-08-15
**平台**: HarmonyOS (OHOS, arm64)
**构建方式**: CMake (cmake 4.1.2) + clang 15.0.4
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: libusb/1.0.27 (Conan ohpcd 制品仓)
**补丁**: 8 个（portability 类：编译 flag、头文件布局、64→32 窄化强转、CMake include 绝对路径）

## 上游测试清单

stlink 1.8.0 上游 CMake 工程在 `tests/CMakeLists.txt` 注册了 3 个 ctest 入口：
`test-usb`、`test-sg`、`test-flash`。

| # | 测试 | 描述 | 结果 | 说明 |
|---|------|------|------|------|
| 1 | test-flash | flash_opts 命令行解析纯逻辑测试（无硬件依赖） | ✅ PASS | 18/18 用例通过，0 FAIL（`[OK]` 断言逐条输出） |
| 2 | test-usb | USB 探测/复位测试 | ⏸ 平台限制 | 需物理 ST-LINK 适配器（`stlink_open_usb()`），沙箱无 USB 设备 |
| 3 | test-sg | SG（SCSI generic）传输测试 | ⏸ 平台限制 | 需物理 ST-LINK 适配器 + root 卸载 usb-storage |

**通过**: 1 个可运行入口 18/18 用例 | **平台限制**: 2 个（需真实 ST-LINK 硬件）

test-flash 实际运行输出（节选）：
```
[OK] (0) --debug --freq 5k --reset write test.bin 0x80000000
[OK] (0) --debug --freq 15k --reset write test.bin 0x80000000
[OK] (0) --debug --reset read test.bin 0x80000000 1M
[OK] (0) --debug --reset write test.bin 0x80000000
[OK] (0) erase
[OK] (0) --serial ABCEFF544851717867216044 erase
```
退出码 0，`[OK]` 计数 18，FAIL 计数 0。

## 消费者测试（test_package）

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | test_stlink (ctest) | 链接 libstlink 调用 `stlink_parse_ihex()` 解析真实 Intel HEX 数据，断言 begin=0x0100 / size=16 / 首尾字节 | ✅ PASS (1/1) |
| 2 | st-info --version | 安装产物 CLI 冒烟（无需硬件） | ✅ 输出 v1.8.0 |

断言计数：test_stlink 内 5 个真实断言（rc、begin、size、mem[0]、mem[15]），
另加 st-info --version 输出校验。无 self.run("true") 空壳。

## 平台限制说明

- **test-usb / test-sg / 设备读写命令**：需要物理 ST-LINK 适配器
  (VID 0x0483, ST-LINK 系列 PID) 和真实目标板，沙箱环境无 USB 设备，
  `libusb_init()` 在该环境返回 -1。属平台限制（E051 类），非适配缺陷。
- **ELF 签名**：鸿蒙平台要求可执行文件和 .so 库 ELF 签名后才能加载
  执行，配方 `package()` 已对 lib/ 和 bin/ 产物统一签名
  (`binary-sign-tool`, SHA256withECDSA)。

## 测试环境

- **Conan 版本**: 2.29.1 (OHOS 适配版)
- **Profile**: ci/conan/profiles/ohos-aarch64
- **上游测试入口**: tests/CMakeLists.txt (add_test × 3)
- **测试命令**: `ctest --output-on-failure`（test-flash 可运行入口）
