# wdisplays — Wayland 显示器布局工具

wdisplays 是一个 GTK+3 图形界面的显示器（output/head）布局工具，通过
Wayland 的 `wlr-output-management-unstable-v1` 协议读取并实时调整各显示器
的分辨率、刷新率、缩放、旋转与相对位置，附带基于 `xdg-output`/
`wlr-layer-shell` 的屏幕名叠加层与基于 `wlr-screencopy` 的截屏预览。

- 上游: https://github.com/artizirk/wdisplays
- 许可: GPL-3.0-or-later
- 语言: C（meson 构建，GTK+3 + wayland-client + libepoxy）

## OHOS PC 适配（1.1.3）

### 关键适配点

1. **GDK Wayland 后端缺失（核心阻塞）**
   OHOS 的 GTK 3 包（gtk/3.24.43）以 broadway(HTML5) 后端构建，
   `gdk-3.0.pc` 的 `targets=broadway`，既没有 GDK Wayland 后端也没有
   `<gdk/gdkwayland.h>`；而上游 `src/main.c`、`src/overlay.c` 直接依赖
   `gdk_wayland_display_get_wl_display()` / `gdk_wayland_monitor_get_wl_output()` /
   `gdk_wayland_window_get_wl_surface()` / `GDK_IS_WAYLAND_DISPLAY`。
   补丁 `0001-ohos-gdkwayland-compat.patch` 新增
   `src/gdkwayland-compat.{c,h}`，以 wayland-client（OHOS 制品仓已有）实现
   这些访问器：
   - `wl_display` 来自真实 `wl_display_connect(NULL)`；
   - `wl_output` 来自 `wl_registry` 绑定；
   - Broadway 窗口背后没有 `wl_surface`，访问器如实返回 `NULL`，
     `main.c`/`overlay.c` 对 `NULL` 做安全降级（不崩溃）；
   - `GDK_IS_WAYLAND_DISPLAY` 语义化为“本进程是否建立了 Wayland 连接”。
   同时把 `src/meson.build` 中“GDK 必须含 wayland 后端”的硬断言放宽为
   “wayland 或 broadway 二者之一”。

2. **构建期工具在 HMFS 上的执行/依赖解析**
   - wayland 包 `bin/wayland-scanner` 直接执行报 EPERM（未签名 ELF），
     且 `DT_NEEDED` 记录构建机缓存绝对路径（loader 不查 LD_LIBRARY_PATH）；
     配方 staging 时 `patchelf --replace-needed` 改写为 soname、重签名，
     再由 wrapper 注入依赖 `lib` 目录。
   - `gnome.compile_resources` 需要 `glib-compile-resources`
     （glib 包 `bin/` OHOS ELF），同样 staging + 重签名，并把
     `glib_compile_resources` 变量注入 `gio-2.0.pc`。

3. **pkg-config 变量补全**
   `wayland-protocols.pc` 需提供 `pkgdatadir`（协议 XML 目录）；
   `gdk-3.0.pc` PkgConfigDeps 不生成（gtk 配方未声明 gdk 组件），
   配方手工生成并置 `targets=broadway`；`glib-2.0.pc` 补 `-lintl`。

### 依赖（制品仓均已发布，conan download/install 验证可消费）

| 依赖 | 版本 | 说明 |
|------|------|------|
| gtk | 3.24.43 | broadway 后端，提供 gtk+-3.0/gdk-3.0 |
| wayland | 1.22.0 | wayland-client + wayland-scanner |
| wayland-protocols | 1.36 | xdg-shell / xdg-output 协议 XML |
| libepoxy | 1.5.10 | 经 gtk 传递（OHOS 为静态 .a） |
| expat | 2.8.2.1 | wayland 传递依赖，override 统一版本 |

### 上游测试

上游**无自动化测试**：源码树无 `tests/` 目录，4 个 `meson.build` 中不含
任何 `test()`/`benchmark()` 注册（甚至不含 `test` 字样），仓库无
`.github/` workflow、无 CI 配置文件。核验证据见
[1.1.3/notes.md](1.1.3/notes.md)。

本适配新增的鸿蒙特有测试在 `test_package/test.sh`（9 条断言：产物存在、
AArch64、`.codesign` 段、libwayland-client/libgtk-3 动态链接、libepoxy
静态链接、GDK-Wayland 兼容层符号、GResource 编入、真机 `--help` 运行）。

### 已知平台限制

OHOS GDK 不含 Wayland 后端、系统也不提供 wlr-output-management compositor，
因此 wdisplays 在 OHOS 上**可以编译、链接、加载并启动**（`--help` 正常），
但完整交互功能需要在具备该协议 compositor 的 Wayland 会话中运行。
