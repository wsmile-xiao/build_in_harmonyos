# libupnp

libupnp (Portable UPnP SDK) 是一个用于开发 UPnP 设备和控制的跨平台 C 库。

## 描述

UPnP（通用即插即用）是一套网络协议，允许设备在家庭网络中无缝发现彼此并协作。libupnp 提供了：

- UPnP 设备架构实现
- SOAP 控制协议支持
- 事件订阅和通知机制
- HTTP 服务器/客户端功能

## 编译信息

- **版本**: 1.18.5
- **构建系统**: CMake（绕过autotools HMDFS限制）
- **编译器**: clang 15.0.4
- **平台**: OpenHarmony aarch64

## 产物

- libixml.so, libixml.a（XML解析库）
- libupnp.so, libupnp.a（UPnP核心库）
- 头文件: upnp/*.h（24个文件）
- 示例程序: tv_ctrlpt, tv_combo, tv_device

## 补丁

- 0001-build-aux-config.guess.patch: 添加 HarmonyOS/OpenHarmony 平台检测
- 0002-build-aux-config.sub.patch: 添加 ohos 三元组支持

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libupnp 1.18.5
```

## 用途

适用于智能家居设备发现、媒体服务器/客户端、IoT 设备互连等场景。
