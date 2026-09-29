# kcemu

`kcemu` 是 KC85/CCS（及多种东德/苏联家用计算机）模拟器，C++ / autotools 工程。

## 适配要点

- **GTK+2 完整栈在本环境无法构建**（`gtk2` 依赖链里的 `pango` 需要 meson，制品仓只有 recipe 没有二进制）。配方改为：写一个 **stub `gtk+-2.0.pc`（只暴露 glib）**让 `configure` 的无条件 `PKG_CHECK_MODULES(GTK,...)` 通过，然后**只构建与 GUI 无关的部分**：`libprefs`/`libdbg`/`libsys_unix` 三个库、6 个命令行工具与上游 `t_prefs`。
- **z80ex**（硬依赖，制品仓没有）：配方在 `source()` 取 z80ex 1.1.21，`build()` 里用 clang 把 `z80ex.c` / `z80ex_dasm.c` 编成静态库并装到本地 prefix。
- **autotools**：用真机自带的 `autoreconf`（Conan 的 perl 包在本机加载不了自己的 XS 模块）。
- 补丁 1 个：`configure.ac` 的 `AM_CONFIG_HEADER`（automake ≥1.13 已废弃）→ `AC_CONFIG_HEADERS`。
- 桩宏：`config/m4/sdl.m4` 提供空的 `AM_PATH_SDL`（`--disable-sound` 时仍会被 autoconf 展开）。
- **E011 规避**：`sed -i 's/umask 077/umask 022/g' configure`（HMDFS + autoconf 临时目录权限问题，见知识库 E011）。

## 上游测试

上游测试套件声明 3 个 `TESTS`（`t_prefs`、`t_memstream`、`t_load`），但 `configure.ac` **硬编码 `AM_CONDITIONAL(HAVE_CPPUNIT, false)`**，后两个从不构建；实际只跑 `t_prefs`。配方构建并实跑 `t_prefs`（通过）。

## 消费者测试

`test_package/test_kcemu.cpp`：链接安装后的 `libprefs.a`/`libdbg.a`/`libsys_unix.a` + glib，做 `Preferences` init / `find_profile` / `set_int_value` / `save`，4 项断言。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/kc2img`、`bin/kc2tap`、`bin/kc2wav`、`bin/kc2raw`、`bin/tdtodump`、`bin/kctape` | 命令行工具 |
| `lib/libprefs.a`、`lib/libdbg.a`、`lib/libsys_unix.a` | 核心静态库 |
| `include/kc/**`、`include/sys/**`、`include/libdbg/**` | 头文件 |

## 已知限制

- 未构建 GUI（`kcemu` 本体，GTK+2 栈在本环境不可用）与 X11 专用 `kcemu-remote`。命令行工具与偏好/调试/系统库完整可用。

## 参考

- 上游：<https://github.com/redcode/kc85_emu>
