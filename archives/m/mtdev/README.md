# mtdev

**描述**: Multitouch Protocol Translation Library - 多点触控设备转换库

mtdev 是一个独立的库，用于将所有内核 MT（Multitouch）事件变体转换为 slotted type B 协议。输入到 mtdev 的事件可能来自任何 MT 设备，特别是：
- Type A（无接触跟踪）
- Type A（有接触跟踪）
- Type B（有接触跟踪）

mtdev 是 libinput 的依赖库，用于处理多点触控设备的输入事件转换。

**官方网站**: https://bitmath.org/code/mtdev/

**许可证**: MIT (X11) License

**维护者**: Henrik Rydberg, Canonical Ltd.

## 编译信息

**构建系统**: autotools

**依赖**: 无特殊依赖

**平台适配**: 
- 需要修改 config.guess 和 config.sub 以识别 HarmonyOS 系统
- 需要在 config.sub 中添加 `linux-ohos*` 内核-OS 组合

## 版本历史

- 1.1.7 (2024-04-05): 构建维护版本
- 1.1.6 (2020-01-26): 构建维护版本
- 1.1.5 (2014-02-28): 构建维护版本