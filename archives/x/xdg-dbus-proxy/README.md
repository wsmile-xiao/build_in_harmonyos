# xdg-dbus-proxy

D-Bus 过滤代理 — 用于 Flatpak 应用沙箱的 D-Bus 连接过滤。

## 简介

xdg-dbus-proxy 是 Flatpak 项目的一个组件，充当 D-Bus 连接的过滤代理。它监听 Unix 域套接字，为每个新连接打开到 D-Bus 总线守护进程的连接，并根据安全策略过滤消息。

策略分为三个级别：
- **SEE**: 名称/ID 可见，可查询
- **TALK**: 可发送方法调用和信号，接收广播
- **OWN**: 可请求/释放/排队名称

## OpenHarmony 编译说明

- 构建系统: Meson (0.1.7 版本弃用了 autotools)
- 依赖: glib/2.88.0.1 (glib-2.0, gio-2.0, gio-unix-2.0)
- gio-unix-2.0.pc 需在 conanfile.py generate() 中手动创建（glib 组件未定义此 .pc）
- 测试需要运行中的 D-Bus session daemon，CI 环境不可用，故禁用
- CI worker 的 AR/AS/STRIP 等工具需通过绝对路径注入 MesonToolchain

## 许可证

LGPL-2.1-or-later

## 主页

https://github.com/flatpak/xdg-dbus-proxy

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 0.1.7 | 2026-08-27 | built | aarch64 构建，Meson 构建系统 |
