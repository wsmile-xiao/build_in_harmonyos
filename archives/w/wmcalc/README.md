# wmcalc

WindowMaker 系的 X11 dockapp 四则计算器：64x64 的 pixmap 小窗，设计成常驻在
WindowMaker 的 dock 或 AfterStep 的 Wharf 里，也可在任意窗口管理器下作为普通窗口运行。
代码由 Edward H. Flora 原创，现由 Window Maker Developers Team 维护
（`wmaker-dev@googlegroups.com`），许可为 GPL-2.0-only。

## 功能面

- 四则运算与显示条（数字/运算符全部由包内 `backdrop.xpm`、`calcbuttons.xpm`、
  `charmap.xpm`、`mask.xbm` 贴图驱动，运行期依赖 libXpm）
- 命令行选项（与 `wmcalc.1` 同源）：`-g <geometry>`、`-d <display>`、
  `-f <filename>`、`-v`（verbose）、`-h`（帮助）
- 配置文件：用户级 `$HOME/.wmcalc`；全局级 `CONFIGGLOBAL = <sysconfdir>/wmcalc.conf`
- 桌面集成：`share/applications/wmcalc.desktop`、
  `share/icons/hicolor/48x48/apps/wmcalc.png`、man1 手册页

## OHOS adaptation

- Builds with its own autoconf 2.69 release tarball (no autoreconf needed) in
  forced cross mode `--build=aarch64-unknown-linux-gnu
  --host=aarch64-unknown-linux-ohos`, driven by `/system/bin/sh`.
- Links the published `libx11/6.4.0` + `libxext/6.4.0.1` + `libxpm/3.5.17`
  (+ `xorgproto/2025.1` headers) cmd-pkgs track, so the XPM pixmap surface is
  kept intact instead of being patched out.
- The six `PKG_CHECK_MODULES` flags are injected as build-time environment
  variables (`X11_CFLAGS/X11_LIBS`, `XEXT_*`, `XPM_*`), which is the documented
  pkg.m4 escape hatch and removes the need for a `pkgconf` tool_requires.
- No source patch: `patches/` is empty; the generated `configure` copy inside
  the Conan build folder is the only thing adjusted (`umask 077` → `022`,
  `ac_pwd` fallback to `$PWD`).
- Upstream ships zero automated tests; the consumer test runs the real binary
  with 6 assertions, including the display-less failure path (`-d :99` →
  exit code 81, `ERR_X_DISPLAY`).

## Dependencies

- `libx11/6.4.0`, `libxext/6.4.0.1`, `libxpm/3.5.17`, `xorgproto/2025.1`
  (all published OHOS armv8 binaries in the `ohpcd` Conan remote)
- libm from the toolchain (`AC_SEARCH_LIBS([pow], [m])`)

## Limitations on HarmonyOS PC

- There is no real X display on the device, so the dockapp main path (window
  creation, pixmap blitting, event loop) cannot be exercised; verification
  stops at the honest `Could not open display` failure.
- Upstream hardcodes `/tmp/wmcalc.tmp` for its temporary config file and
  `<sysconfdir>/wmcalc.conf` for the global config. On OHOS `/tmp` is
  read-only and `/etc` is not populated by packages, so the "save options"
  branch fails by construction. Declared as-is; not patched away.

## References

- Upstream homepage (aggregator): https://www.dockapps.net/wmcalc
- Release tarball: https://www.dockapps.net/download/wmcalc-0.7.tar.gz
- Maintainer list: wmaker-dev@googlegroups.com (Window Maker project)
