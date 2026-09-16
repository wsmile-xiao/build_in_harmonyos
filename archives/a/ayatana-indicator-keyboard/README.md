# ayatana-indicator-keyboard

Ayatana Indicators 键盘指示器 D-Bus 服务，注册 `org.ayatana.indicator.keyboard` bus 名，
提供键盘布局切换菜单（外接键盘 HWKBD / 屏上键盘 OSK），面向 Unity/MATE/Lomiri 等桌面。

- 上游仓库: https://github.com/AyatanaIndicators/ayatana-indicator-keyboard
- 构建系统: CMake (cmake_minimum 3.13)
- 依赖: glib-2.0 >= 2.36, gio-2.0 >= 2.36, libayatana-common >= 0.9.11,
  accountsservice, xkbcommon >= 1.0.3, xkbregistry >= 1.0.3, libudev,
  x11 >= 1.6.5, libxklavier >= 5.3
- 许可证: GPL-3.0

## 版本

- 26.6.2 — 最新稳定版

## 产物

- 服务可执行文件 `ayatana-indicator-keyboard-service`（安装于 `bin/`）
- 键盘后端插件 `lib/libayatana-keyboard-x11.so.0` 与 `lib/libayatana-keyboard-lomiri.so.0`
 （服务运行时按桌面环境经 `dlopen` 二选一加载）

OHOS 适配说明见 `26.6.2/notes.md`。

## 已知限制

- `data/`（GSettings schema / systemd 单元 / autostart）与 `po/` 在 OHOS 构建中跳过
 （SKIP_DATA_PO=ON，本仓无 GSettings/Intltool CMake 模块，同族
  ayatana-indicator-session 26.6.1 相同处理）。
- 上游无测试框架（无 `tests/` 目录、无 CTest 接线），适配后由 `test_package`
  冒烟（`--version` / `--help`）补全覆盖。
- `accountsservice`（`act/act.h`）全仓暂无配方，`xkbregistry` 在现有
  `libxkbcommon/1.6.0` 配方中被禁用——两者需先行适配（W0/R36），
  首轮工作树如实声明，待 HMBS 真机预检确认。
