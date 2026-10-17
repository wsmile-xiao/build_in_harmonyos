# XClicker

XClicker 是一个面向 X11 桌面、基于 GTK3 的快速图形化自动点击器（autoclicker），
通过 XTest/XInput2 向 X 服务器注入鼠标与键盘事件。

## 功能概述

- 图形界面（GTK3 + GtkBuilder `.ui` 资源）设置点击参数
- 可调点击间隔（时/分/秒/毫秒）、随机化间隔
- 鼠标按键（左/中/右）、点击类型（单击/双击/按住）、按住时长
- 安全模式（Safe Mode）防止误触发
- 自定义热键启停、按住热键连点
- 重复指定次数或持续点击
- 指定坐标点击
- 配置持久化（GKeyFile，`$XDG_CONFIG_HOME/xclicker.conf`）

## OHOS 适配

- **构建系统**：使用上游 `meson.build`（根 `Makefile` 仅封装 `meson`+`ninja`，
  且其中 `executable()` 未声明 `install: true`，`meson install` 不安装产物，
  配方在 `package()` 中显式拷贝 `src/xclicker`）。
- **依赖**：GTK3 复用 main 上已适配的 `gtk/3.24.43`；X11 侧使用
  `libx11/6.4.0`、`libxi/6.1.0`、`libxtst/6.1.0`（按 `.so` 主版本命名的同源一组）。
- **构建期工具**：`gnome.compile_resources` 需要 `glib-compile-resources`。
  制品仓 `glib` 包的 `bin/` 未签名、且 Meson 的 `[binaries]` 未提供该工具，
  配方从 glib 包复制该工具到构建目录、OHOS 下签名，并注入
  `conan_meson_native.ini` 的 `[binaries]`（同 gtk/gdk-pixbuf 既有方案）。
- **链接器**：`MesonToolchain` 生成的机器文件只写 `c`/`cpp`，meson 会去探测
  clang 默认的 `llvm-ar`/`llvm-ranlib`；配方按 SDK bin 注入绝对路径，
  消除对构建 env `PATH` 的隐式依赖。
- **签名**：OHOS 下对 `bin/xclicker` 执行 `binary-sign-tool` 自签名
  （未签名 ELF 不可执行）。
- **已知限制**：沙箱/CI 无 X display，GTK 无法进入主循环，因此仅做
  `--help` 级运行验证（该命令在 `main()` 前加载全部动态依赖，等价于
  运行期依赖闭包检查），不做 UI 交互测试。

## 依赖关系

- 编译/运行依赖：`gtk/3.24.43`、`libx11/6.4.0`、`libxi/6.1.0`、`libxtst/6.1.0`
  （及 gtk 传递依赖 glib/cairo/pango/gdk-pixbuf/atk 等）
- 无上游测试依赖

## 参考资料

- 源码仓库：https://github.com/robiot/xclicker
- 官网：https://xclicker.xyz
- 许可证：GPL-3.0-only
