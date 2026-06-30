# bluez-alsa

> Bluetooth ALSA audio bridge for Linux BlueZ stack

## 简介

bluez-alsa 提供 BlueZ 蓝牙协议栈与 ALSA 音频子系统之间的桥接，支持 A2DP（高级音频分发协议）和 HFP（免提协议）音频流。包含 bluealsa 守护进程、bluealsa-aplay 回放工具和 ALSA 插件模块。

## OHOS 适配要点

- OHOS 缺少 pthread_cancel 和 pthread_setcancelstate 实现，需添加 stub 兼容层（#ifdef __OHOS__ 守卫）
- HMDFS 上 autotools config.status 存在临时文件权限问题，可通过 touch stamp-h1 绕过
- autotools 构建需要先运行 autoreconf -fi（从 GitHub tarball）
- config.guess/config.sub 需修补以支持 HarmonyOS 平台

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| alsa-lib | 1.2.12 | ALSA 音频库 |
| bluez | 5.79 | 蓝牙协议栈 |
| dbus | 1.15.8 | D-Bus 通信 |
| glib | 2.84.0 | GLib 工具库 |
| sbc | 1.5 | SBC 音频编解码 |

## 功能验证

```bash
bluealsa --help
bluealsa-aplay --help
```

## 参考

- [源码仓库](https://github.com/arkq/bluez-alsa)