# scrcpy - Android 屏幕镜像工具

scrcpy 是一个高性能的 Android 屏幕镜像和控制工具，通过 USB 或 TCP/IP 连接显示和控制 Android 设备。

## 功能特性
- 高性能镜像（30~120fps）
- 低延迟（35~70ms）
- 高分辨率（1920x1080 或更高）
- 音频转发
- 录屏
- 多设备支持
- HID/OTG 模式（无需 adb）

## 依赖
- SDL2 >= 2.0.5
- ffmpeg >= 57.x
- libusb-1.0（可选，用于 OTG 模式）
- adb（android-tools）

## 已编译版本
- 2.3.1 (2026-05-22)

## 使用方法
```bash
# 设置库路径
export LD_LIBRARY_PATH="$HOME/usr/local/lib:$LD_LIBRARY_PATH"

# 运行
scrcpy --serial=<device-id>
```

## 注意事项
- 需要下载对应的 scrcpy-server
- HMDFS 动态库加载需要设置 LD_LIBRARY_PATH
