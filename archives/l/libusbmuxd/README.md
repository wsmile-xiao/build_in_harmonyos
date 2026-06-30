# libusbmuxd

## 简介

libusbmuxd 是一个用于通过 USB 与 iOS 设备通信的库，提供了设备发现和连接管理功能。

## OHOS 适配

- **autotools 适配**：需要移除 config.status 中的 `umask 077`（HarmonyOS TMPDIR 权限限制）
- **依赖变化**：libusbmuxd 2.x 版本依赖 libimobiledevice-glue（1.x 版本不依赖）
- **pkg-config 名称**：使用 `libusbmuxd-2.0`

## 依赖

- libplist >= 2.3.0
- libimobiledevice-glue >= 1.3.0

## 功能验证

```bash
pkg-config --modversion libusbmuxd-2.0
# 输出: 2.1.0
```

## 参考

- 官网: https://libimobiledevice.org/
- 源码: https://github.com/libimobiledevice/libusbmuxd