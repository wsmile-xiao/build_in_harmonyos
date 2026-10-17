# gtk-vnc 1.5.0 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build）
- 编译日期: 2026-09-02
- 编译器: clang/clang++（OHOS SDK 15.0.4）
- 状态: built

## 编译步骤

1. 官方源: https://download.gnome.org/sources/gtk-vnc/1.5/gtk-vnc-1.5.0.tar.xz（含 keycodemapdb subproject）
2. `conan create` 驱动 meson 构建：
   - `meson setup --native-file <conan_meson_native.ini> <build> <src>`
   - `meson compile` + `meson test`（上游测试 coroutinetest / vncconnectiontest 全通过）
3. 依赖经 ohpcd 制品仓发布：glib/gtk/gdk-pixbuf/gnutls/gmp/zlib/cairo

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 探测 python 报 exit 127 / "missing distutils" | conan build env 注入的依赖 libdir 含缺符号的 OHOS libintl.so.8，python3.12 加载即崩溃 | 构建环境不向 LD_LIBRARY_PATH 注入依赖 libdir（configure/compile 无需运行时库路径）；glib 工具与 python3 用 wrapper 清空 LD_LIBRARY_PATH |
| 2 | 链接报 undefined symbol: g_libintl_bindtextdomain / g_libintl_textdomain | glib-2.0.pc 缺 -lintl 链接 | `_augment_glib_pkg_config` 给 glib-2.0.pc 的 Libs 行补 `-lintl`（参考 gtk 配方） |
| 3 | meson 生成畸形命令 `<builddir>/-c`（ninja 编译期 FAILED） | meson wrapper 用 `python3 -c '...'` 启动导致 sys.argv[0]='-c'，meson 推导自身命令时拼到构建目录 | 改 `python -m mesonbuild.mesonmain`（argv[0] 为真实路径） |
| 4 | test_package 运行时缺 libgnutls.so.30 / libc++_shared.so | conanrun env 缺个别传递依赖 libdir；SDK C++ 运行时不在路径 | test_package test() 显式收集全部 host 依赖 libdir + SDK libc++_shared.so 目录，用包装脚本注入 LD_LIBRARY_PATH |
| 5 | test_package 创建 GTK widget 崩溃（Signal 11） | OHOS 无显示环境，实例化 GtkVncDisplay 崩溃 | 改为仅验证类型注册 `vnc_display_get_type()`（不实例化 widget） |
| 6 | zlib/gmp 版本冲突 | 依赖图对 zlib/gmp 版本要求不一致 | 对齐 glib/gdk-pixbuf/cairo 的 zlib/1.3.1.1、gnutls 链的 gmp/6.3.0 |

## 源码修改

无补丁（patches/ 为空）。所有适配修复均在 conanfile.py / test_package 配方层完成（GLib 工具 wrapper、-lintl 注入、libintl 规避、meson 工具链注入、.so 签名）。

## 依赖版本

- glib/2.84.0.1
- gtk/3.24.43
- gdk-pixbuf/2.44.6.1
- gnutls/3.8.10
- gmp/6.3.0
- zlib/1.3.1.1
- cairo/1.18.4

## 验证结果

```bash
# conan-verify G2（conan create）：
#   G1-G4 + L2/L4/L5 全部 PASS
# 上游测试（meson test）：
#   gtk-vnc:coroutinetest      OK
#   gtk-vnc:vncconnectiontest  OK
#   Ok: 2  Fail: 0
# test_package 消费者测试：
#   gtk-vnc test: OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 构建配方（GLib 工具链 + 签名 + 依赖声明） |
| conandata.yml | 官方源 download.gnome.org + sha256 |
| test_package/ | 消费者测试（PkgConfig 方式） |
| commands.json | gvnccapture 命令行工具声明 |

## 注意事项

- gtk-vnc 属 GTK UI 库：适配重点是库可链接、类型系统可注册；实际 widget 渲染/显示依赖运行环境（E463 无显示环境限制），test_package 只覆盖连接 API 与类型注册，不实例化 widget（R40 需人工确认显示路径）。
- meson 工具链（python3/ninja）在 OHOS 环境有 libintl 加载限制，依赖 wrapper 注入，CI 与本地需保持一致的 build env。
- gvnccapture 为命令行工具，已按 R38 声明 commands.json。

**编译结束**: 2026-09-02 02:32
**最终状态**: built
