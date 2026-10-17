# ayatana-indicator-power — Ayatana Power Indicator

## 软件简介

ayatana-indicator-power 是 Ayatana Indicators 项目中的电源状态指示服务
（D-Bus session service）。它监听电池电量、充放电状态与屏幕亮度变化，
向桌面通知（libnotify）与指示器框架发布状态，并在电量过低时弹出通知。

上游使用 CMake 构建，核心依赖 glib/gio/gio-unix（≥2.36）、libayatana-common
（≥0.9.1）、libnotify（≥0.7.6），可选 RDA（remote desktop awareness）。

**主要功能**:
- 电池/亮度设备枚举与状态监听（UPower 或 mock provider）
- D-Bus 导出 `org.ayatana.indicator.power` 对象与 `Battery`/`Testing` 接口
- 电量临界/过低/低时通过 libnotify 弹出桌面通知
- 支持 Lomiri 特性（可选）、deviceinfo 闪光灯（可选）、RDA（可选）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 26.6.0 | built ✅ | 2026-09-05 | 1 |

## 平台适配说明（HarmonyOS PC / OHOS aarch64）

- 构建系统为 **CMake**（`pkg_check_modules` 解析 glib-2.0/gio-2.0/gio-unix-2.0/
  libnotify/libayatana-common），PkgConfigDeps 生成 `.pc` 后需两个补充：
  * glib 配方缺 `gio-unix-2.0.pc` → 从 glib 包目录合成；
  * glib 的 proxy-libintl 提供 `g_libintl_*` 符号但 `.pc` 未列 `-lintl` → 追加。
- OHOS 无 intltool 可执行 → 补丁新增 `SKIP_PO` 选项跳过 `po/` 子目录。
- `data/CMakeLists.txt` 原 `XDG_AUTOSTART_DIR=/etc/xdg/autostart` 为绝对路径，
  会写出 package 目录之外 → 补丁改为 `${CMAKE_INSTALL_PREFIX}` 相对路径。
- `main.c` 增加 `--version/--help` 支持：D-Bus 服务在 OHOS PC 无 session bus，
  原始程序会进入 `g_main_loop` 阻塞；加参数处理使服务可被 smoke test 验证。
- RDA（librda）未发布到制品仓 → `ENABLE_RDA=OFF` 关闭可选特性（R36 记录）。
- cmake-extras 提供 GSettings CMake 模块，作为构建期依赖引入。

## 使用方法

```bash
# 查看版本
ayatana-indicator-power-service --version
# 帮助
ayatana-indicator-power-service --help
# 正常以 D-Bus session service 方式运行（OHOS PC 需先有 session bus）
ayatana-indicator-power-service
```

## 依赖

- glib/2.88.0.1
- libayatana-common/0.9.13
- libnotify/0.8.3.1
- cmake-extras/1.9（构建期，提供 GSettings 模块）
