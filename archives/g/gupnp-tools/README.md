# gupnp-tools

GUPnP Tools — Intel UPnP tools 的自由替代品。上游包含：

- **gssdp-discover**（CLI）：SSDP 资源发现工具（打印局域网内 UPnP 设备/服务通告）
- **gupnp-event-dumper**（CLI）：订阅 UPnP 服务事件并实时打印状态变量变化
- gupnp-network-light（GUI）：虚拟灯泡（演示设备）
- gupnp-universal-cp（GUI）：通用控制点
- gupnp-av-cp / gupnp-upload（AV）：媒体控制点/内容上传（依赖 gupnp-av）

- 上游：https://gitlab.gnome.org/GNOME/gupnp-tools
- 构建系统：meson
- 许可证：GPL-2.0-or-later

## 鸿蒙适配要点

1. **CLI-only 构建**（补丁 0001）：GUI 工具硬依赖 GTK+ 3；已发布的
   gtk/3.24.43（broadway HTML5 后端）绑定的是独立的 shared glib/2.84，
   而 gupnp 协议栈（glib2/2.88 static + libsoup-3.0.so 单 GObject 域）
   在同一进程引入第二份 GObject 域会导致 GType 注册撕裂 SIGABRT
   （gssdp 1.6.6 / gupnp 1.6.8 notes 本地铁证）。故鸿蒙适配裁剪 GUI
   工具，构建 gssdp-discover + gupnp-event-dumper 两个 CLI 工具
   （它们上游本来就不依赖 GTK）。
2. **依赖栈**：gssdp/1.6.6 + gupnp/1.6.8 + libsoup3/3.6.5-r1 +
   glib2/2.88.0（静态，.pc Libs 置空方案）+ libxml2/2.15.3。
   ⚠️ gupnp/1.6.8 依赖 PR #8316（open 未合）——其发布前本包被 PF4
   依赖闸拦截推送（本地全套路验证先行完成）。
3. **无上游测试**：工具集项目无 tests/ 目录；验证 = 实际运行工具
   （test_package 执行 --help 真实冒烟）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.12.4 | built | CLI 工具集（gssdp-discover / gupnp-event-dumper） |
