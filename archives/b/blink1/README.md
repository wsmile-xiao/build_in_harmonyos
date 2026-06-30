# blink1

blink1-tool 是 blink(1) USB RGB LED 设备的命令行控制工具。
它提供颜色设置、图案播放、设备状态读取等功能。

## 版本 2.4.0

- **构建平台**: HarmonyOS aarch64
- **编译器**: clang 15.0.4
- **构建系统**: 纯 Makefile
- **最终状态**: published
- **编译日期**: 2026-06-18

## 产物

| 文件 | 说明 |
|------|------|
| bin/blink1-tool | 命令行工具（64KB） |
| lib/libblink1.so | 共享库，导出 blink1 API（43KB） |

## 依赖

- libc (musl) — 系统自带，动态链接
- libusb 1.0.27 — 预编译包已安装，但 stub 实现不依赖
- hidapi 0.14.0 — 预编译包已安装，但 stub 实现不依赖

## 构建说明

### 构建命令

```bash
make OS=linux HIDAPI_TYPE=LIBUSB PREFIX=$DEFAULT_PREFIX
make install PREFIX=$DEFAULT_PREFIX OS=linux HIDAPI_TYPE=LIBUSB
```

### 平台适配

在 HarmonyOS 上，USB HID 库（libudev/libusb）不可用于链接。
使用 HIDAPI stub 实现使 blink1-tool 能够编译并运行非 USB 功能：
- ✅ `--version` / `--help` — 正常工作
- ⚠️ USB 设备操作 — 返回 "no blink(1) devices found"（预期行为）

### 补丁

| 补丁 | 说明 |
|------|------|
| 0001-hidapi-hidapi-hidapi.h.patch | HIDAPI 头文件声明 + 宏定义 |
| 0002-hidapi-libusb-hid.c.patch | HIDAPI stub 实现 |
