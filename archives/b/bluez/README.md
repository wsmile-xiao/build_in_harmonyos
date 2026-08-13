# BlueZ — OpenHarmony 编译档案

## 软件简介
BlueZ 是 Linux 官方蓝牙协议栈，提供核心蓝牙守护进程（bluetoothd）与命令行工具集（bluetoothctl、btmon 等）。

## 功能概述
- bluetoothd: 蓝牙核心守护进程（BR/EDR + LE）
- bluetoothctl: 交互式命令行客户端
- btmon: 蓝牙协议监视器
- btattach: 串口蓝牙适配器绑定工具
- hex2hcd: HCD 固件转换工具
- l2ping/rctest/isotest: 蓝牙链路测试工具
- 完整协议实现: GATT/SDP/AVDTP/AVRCP/HFP/BAP 等

## OHOS 适配要点
- config.guess/config.sub 增加 HarmonyOS 识别（E007）
- configure umask 077→022 修复 HMDFS 临时目录权限（E011）
- 禁用 udev/systemd 集成（OHOS 无 systemd）；禁用 OBEX profile（libical 未发布）
- gdbus/object.c 补充 MAX_INPUT musl 兼容定义
- tools/obexctl.c rindex()→strrchr()（musl 无 BSD 遗留函数）
- android/avdtp.c set_priority() 容忍 SO_PRIORITY EPERM（沙箱无 CAP_NET_ADMIN）
- unit/test-textfile 改用 TMPDIR（/tmp 只读，E002）

## 依赖关系
- 必需: glib/2.84.0.1、dbus/1.14.10、readline/8.3（制品仓已发布）
- ell: 使用 bluez 内置版本

## 版本历史
| 版本 | 状态 | 说明 |
|------|------|------|
| 5.79 | published | 首次适配 |
