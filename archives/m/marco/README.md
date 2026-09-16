# marco

marco 是 MATE 桌面环境的窗口管理器（X11 合成窗口管理器）：负责窗口装饰绘制、
移动/缩放、工作区、键绑定、窗口列表与 EWMH 属性、XRender 合成器。本仓库提供其
在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

https://github.com/mate-desktop/marco

## 许可证

GPL-2.0-or-later

## 产物

| 类型 | 文件 |
|------|------|
| 可执行 | `bin/marco`（窗口管理器）、`bin/marco-message`（向运行中的 WM 发 EWMH 消息）、`bin/marco-window-demo`、`bin/marco-theme-viewer` |
| 共享库 | `lib/libmarco-private.so.2.0.0`（窗口装饰/合成器内部库） |
| 头文件 | `include/marco-1/marco/*.h` |
| 元数据 | `lib/pkgconfig/libmarco-private.pc`、`share/applications/marco*.desktop`、`share/glib-2.0/schemas/org.mate.marco.gschema.xml` |
| 其它 | `share/locale/*/LC_MESSAGES/marco.mo`（112 个语言）、`share/themes`、man 手册 |

## 平台适配要点

1. **GDK-X11 兼容层**（补丁 0001）：制品仓 `gtk/3.24.43` 是 broadway 后端构建，
   不含 `gdk/gdkx.h`、不导出 `gdk_x11_*` 符号；marco 是纯 X11 客户端
   （`GDK_DISPLAY_XDISPLAY` 100 处、`GDK_WINDOW_XID` 13 处、10 个 `gdk_x11_*`
   函数）。兼容层提供单例 X 连接、XID 双向映射、X 错误陷阱与 X 事件过滤器分发，
   仓库先例：`libwnck3/43.3` 的 x11-compat。
2. **Cairo-Xlib 兼容层**（补丁 0005）：制品仓 `cairo/1.18.4` 为
   `xlib=disabled`（无 `cairo_xlib_*` 符号与 `cairo-xlib.h`），而窗口边框渲染
   （`src/ui/ui.c`、`src/ui/frames.c`）与 xrender 合成器需要把 X pixmap 转成
   cairo surface；兼容层用 `XGetImage` + cairo image surface 提供同名入口。
3. **libcanberra-gtk3**（补丁 0002）：`MARCO_PC_MODULES` 无条件要求该模块，
   制品仓 `libcanberra/0.30` 未构建 gtk3 模块；补丁提供等价的
   `ca_gtk_context_get()`，配方生成同名 shim `.pc` 指向真实 libcanberra。
4. **config.guess/config.sub**（补丁 0003）：2023 年版无法识别
   `aarch64-linux-ohos`，且其编译器探针在 OHOS 上无法执行（未签名 ELF 被内核
   拒绝）；补丁增加 HarmonyOS/aarch64-linux-ohos 三元组。
5. **startup-notification / zenity**：两者制品仓均未发布。前者用上游官方开关
   `--disable-startup-notification` 关闭；后者是运行时可选对话框助手
   （`src/core/util.c` 按名字 `"zenity"` 查找），configure 的存在性检查降级为
   警告（补丁 0004 + 配方对生成物 `configure` 的同源机械替换）。

## 运行期说明

marco 是 X11 窗口管理器，运行需要 X server（HarmonyOS PC 目前没有 X server），
因此本适配聚焦"可编译、可加载、契约可测"：无 X server 时兼容层安全降级，
`marco --version` / `--help` 可在无显示环境下正常返回。

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 | 上游测试 | 新增测试断言 |
|------|------|----------|----------|--------|----------|--------------|
| 1.26.2 | built | 2026-09-13 | autotools | 5 | 14/21 用例（可运行项 14/14 = 100%，逐项原因见 notes.md） | 99（24+60+12+3，100%） |
