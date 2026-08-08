# gtk-mac-integration 3.0.2 路径 B 部分适配分析

更新日期：2026-08-07

- 路径 B 类型：无法适配/部分适配
- 认领 Issue：#761
- 路径 B Issue：#927
- 对应 PR：#2730
- 当前结论：可提供可编译的 GObject 兼容层，但无法在 HarmonyOS 上实现该库绑定
  macOS 的核心系统集成语义。

## 已完成范围

当前 PR 提供了 `GtkosxApplication` 的可移植兼容 API，可验证单例、状态、
生命周期信号、注意请求和包路径等不依赖 macOS 系统服务的行为。官方 OHOS
CI Build #11489 曾通过该兼容实现的构建与消费测试。重开后的 Builds #15329、
#15330、#15400、#15581、#15598 和 #15662 已完成兼容库构建。Build #15400 证明当前
`glib/2.84.0` 只导出聚合目标 `glib::glib`，不存在 `glib::gobject`；Build #15598
进一步证明该聚合目标没有向消费测试传递 `GLIB_INCLUDE_DIR` 与
`GLIB_CONFIG_INCLUDE_DIR`。Build #15662 又证明仅在消费测试的 CMakeLists 中引用
这两个变量并不会自动为它们赋值，所以安装头中的 `glib-object.h` 仍无法找到。
消费测试配方现已从 Conan 依赖图中的 `glib` 包目录计算这两个路径，通过
`CMakeToolchain` 显式传给 CMake。兼容库和消费测试始终链接 OHPCD 的聚合目标
`glib::glib`；当其他 GLib 配方额外导出 `glib::gobject` 或
`glib::gobject-2.0` 组件时，也会显式追加相应目标以传播 GObject 依赖。仍需重新
执行官方 CI。

这部分工作属于“部分适配”，不能等同于完整移植 gtk-mac-integration。

## 根因分析

gtk-mac-integration 的核心目标是把 GTK 应用接入 macOS 菜单栏、Dock、应用
Bundle 和 `NSApplication` 生命周期，并非提供通用 GTK 抽象层。上游关键路径
直接依赖：

- Objective-C 编译与运行时；
- Cocoa/AppKit 的 `NSApplication`、`NSMenu`、`NSImage` 等类型；
- GDK Quartz 后端及 `gdk_quartz_*` 接口；
- macOS Bundle、全局菜单栏和 Dock 服务。

HarmonyOS SDK 不提供这些框架或与其行为等价的 ABI/API。它们覆盖的正是该库
的主要功能，不是可通过少量条件宏替换的边缘代码。

## 已尝试方案及结果

1. 直接构建上游源码：配置阶段要求 Objective-C，随后缺少 Cocoa/AppKit 与
   GDK Quartz，无法形成可链接目标。
2. 删除 macOS 专有实现：能够保留少量 GObject 声明，但菜单、Dock、Bundle
   和应用生命周期能力全部消失，不构成完整移植。
3. 提供空桩：虽可绕过编译，却会让公开函数静默失效，违反实质适配和测试要求。
4. 当前 GObject 兼容后端：保留可移植状态与信号语义，并用 11 个失败门槛验证；
   无法提供系统级菜单栏、Dock 或 Cocoa 生命周期，因此仅为部分适配。
5. 使用 ArkUI 重写：需要重新设计对象模型、应用生命周期、菜单和窗口接口，
   无法保持上游 gtk-mac-integration 的 API/ABI 与行为兼容，属于新实现而非移植。

## 测试边界

- 上游自动化功能测试：0 个；`GTKDOC_CHECK` 仅校验文档生成。
- 上游 macOS 集成行为：HarmonyOS 无对应平台服务，无法执行或声明通过。
- 新增兼容层消费测试：1 个程序、11 个失败门槛，只覆盖可移植子集。
- 未验证且不可伪记为通过：全局菜单栏、Dock 菜单、`NSApplication` 委托、
  Quartz 加速键和真实 macOS Bundle 行为。

## 解除条件

只有在目标平台提供与 Cocoa/AppKit、GDK Quartz、macOS 全局菜单/Dock 和应用
生命周期等价的公开接口，或赛事明确允许把该库重新定义为“仅 API 兼容层”时，
才可能继续扩大适配范围。当前提交不把兼容层测试通过写成核心系统集成通过。
