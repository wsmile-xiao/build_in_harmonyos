# stlink 1.8.0 适配笔记

## 三重身份

| 身份 | 值 |
|------|----|
| 平台 | stlink 1.8.0（Issue #2191） |
| 上游 | stlink-org/stlink tag v1.8.0（BSD-3-Clause） |
| 归档 | stlink/1.8.0（archives/s/stlink/1.8.0） |

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-15
- 编译器: clang 15.0.4
- 平台: HarmonyOS (OHOS, arm64)
- 依赖: libusb/1.0.27（Conan ohpcd 制品仓，已发布）

## 编译步骤

stlink 是 CMake 工程（顶层 `cmake_minimum_required(3.10.2)`）：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify stlink 1.8.0   # G0-G4 + L2/L4/L5
python3 $SKILL_ROOT/scripts/ohc-run.py finish stlink 1.8.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-Wshorten-64-to-32` 报错 | clang 15 对 size_t→uint32_t 窄化按硬错误处理 | 补丁 0001 禁用该 flag；补丁 0003-0006 显式强转 |
| 2 | `sys/poll.h` 不存在 | musl 布局的 OHOS libc 无该头 | 补丁 0002 改用 `<poll.h>` |
| 3 | `stlink_serial()` 返回值类型不匹配 | 上游误用 uint32_t 接收 size_t 返回值 | 补丁 0007 改为 size_t |
| 4 | lib/ include/ 未安装 | E092：CMake 不识别 HarmonyOS | `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 5 | 找不到 libusb | 上游 `Findlibusb.cmake` 用 `LIBUSB_INCLUDE_DIR/LIBUSB_LIBRARY` cache 变量 | 配方 `generate()` 从 libusb 依赖包显式解析 |
| 6 | udev/modprobe 安装到绝对路径 | 上游默认 `STLINK_MODPROBED_DIR=/etc/modprobe.d`、`STLINK_UDEV_RULES_DIR=/lib/udev/rules.d` | 配方 cache 变量重定向到包内 `etc/` 下 |
| 7 | 运行时 "Operation not permitted" | 鸿蒙要求 ELF 签名 | 配方 `package()` 对 lib/ .so 与 bin/ 工具统一 `binary-sign-tool` 签名 |

## 源码修改

7 个补丁（均为 portability 类，不改变上游断言、数据、用例选择与预期）：
- 0001: 禁用不兼容编译 flag
- 0002: 头文件路径修正（include 布局）
- 0003-0006: 64→32 位窄化的显式强转（编译兼容）
- 0007: 返回类型修正（size_t）

## 依赖版本

- libusb/1.0.27（Conan ohpcd 制品仓，已发布）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify stlink 1.8.0   # G0-G4 + L2/L4/L5 全过
# 上游测试：test-flash（flash_opts 纯逻辑测试）PASS；test-usb/test-sg 需真实 ST-Link USB 设备
# test_package 消费者测试：stlink_parse_ihex 真实 API 调用 + 断言 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libstlink.so(.1/.1.8.0) | 共享库（已签名） |
| lib/libstlink.a | 静态库 |
| include/stlink/*.h | 头文件（含 version.h） |
| bin/st-flash, st-info, st-util, st-trace | 4 个命令行工具（已签名） |
| share/stlink/chips/*.chip | 芯片配置文件 |
| etc/modprobe.d, etc/udev/rules.d | ST-LINK 设备配置（包内重定向） |

## 注意事项

- `st-info --version` 无需硬件即可运行（打印 v1.8.0），作为 L2 冒烟测试入口。
- `test-usb` / `test-sg` 需要物理 ST-LINK 适配器（`stlink_open_usb()`），
  沙箱无 USB 设备，属平台限制（E051 类），不计入通过用例。
- 设备读写类命令（st-flash write/read、st-util）需真实 ST-LINK 硬件与目标板。
---

**编译结束**: 2026-08-15 22:50
**最终状态**: built
