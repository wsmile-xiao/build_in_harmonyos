# glade 3.40.0 — OHOS PC 适配笔记

## 概览

GNOME 用户界面设计器 Glade（GTK+ 3）。产物：
- `bin/glade` — 设计器主程序（GtkApplication）
- `bin/glade-previewer` — 独立预览器
- `lib/libgladeui-2.so` — 设计时库（IDE 集成用，pkg-config `gladeui-2`）
- `share/glade/catalogs/` — GTK+ 部件目录（XML）
- `lib/glade/modules/libgladegtk.so` — GTK+ 部件 adaptor 插件

构建系统 meson；语言 C（lang-preflight: c，218 源文件 c:215 99%）。

## 依赖（全部 ohpcd 制品仓实测 conan download 通过）

- gtk/3.24.43（broadway 后端构建，无 X11/wayland）
- glib/2.84.0.1（gtk 配方 pin 该版本；2.84.0.1.1 会版本冲突）
- libxml2/2.15.3
- 传递：pango/1.50.14.1.1、gdk-pixbuf/2.44.6.1、atk/2.38.0.1.1、cairo、
  harfbuzz、fribidi、libepoxy 等（由 gtk 带入）

注意：任务预检单里的 pango/1.50.14.1 与 gdk-pixbuf/2.44.6 在图中被 gtk
配方升级为 1.50.14.1.1 / 2.44.6.1（gtk/3.24.43 recipe pin 的版本，R36
依赖图一致性）。requirements 直接声明 gtk/glib/libxml2 三个。

## meson 选项（OHOS 禁用项及原因）

| 选项 | 值 | 原因 |
|---|---|---|
| introspection | false | 无 gobject-introspection 运行时 |
| man | false | xsltproc 需联网取 docbook XSL |
| gjs | disabled | 无 gjs 生态 |
| python | disabled | 无 pygobject 生态 |
| webkit2gtk | disabled | 无 webkit2gtk |
| gladeui | false | gladeui 自建 catalog（设计器自设计），非运行必需 |
| mac_bundle | false | 非 macOS |

## 关键适配点（全部本机实测）

### 1. glib 构建工具 staging（HMFS 双限制）

glib 包 bin/ 下工具两类：
- **python 脚本**（glib-mkenums / glib-genmarshal）：HMFS 拒绝跨 UID
  shebang 执行 → `/bin/sh` wrapper 显式 `exec python3 <脚本>`。
- **OHOS ELF**（glib-compile-resources / glib-compile-schemas）：HMFS 上
  直接执行报 `Operation not permitted`（EPERM，原签名在跨目录执行场景被
  拒）→ 拷贝到 build 目录 + `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool -selfSign 1` 重签后可执行；wrapper 里注入
  `LD_LIBRARY_PATH=<conan glib lib>` 解决其 so 依赖。
- hnp 系统的 glib 2.38 版 glib-compile-resources 不支持
  `--dependency-file`（meson 生成 gresource 时必用），必须用 conan glib
  2.84 的版本。

### 2. PkgConfigDeps pc 修补

- `glib-2.0.pc` 补 `glib_mkenums/glib_genmarshal/gobject_query` 工具变量
  （meson gnome.mkenums 查询）+ **Libs 补 `-lintl`**（glib 2.84 的
  g_libintl_* 符号在 libintl.so；缺失时链接 libgladeui 报
  `undefined symbol: g_libintl_bindtextdomain`）。
- `gio-2.0.pc` 补 `glib_compile_schemas/glib_compile_resources`（meson
  gnome.compile_resources / compile_schemas 查询）。
- **gmodule-export-2.0.pc**：glade 顶层依赖它，glib 包内有但
  PkgConfigDeps 不生成 → 手工写（Libs 带 -Wl,--export-dynamic）。
- **gdk-3.0.pc**：glade 用 `dependency('gdk-3.0').get_pkgconfig_variable
  ('targets')` 判断 quartz；gtk 包内有但 PkgConfigDeps 不生成 → 手工写
  （targets=broadway，Requires gtk+-3.0）。

### 3. meson 裸名 subprocess 坑（NINJA/PATH）

worker 上 Python subprocess 对 PATH 查找的裸名命令一律 ENOENT（含
meson 的 ninja 探测与 ELF 工具调用）。规避：
- machine file `[binaries]` 注入 ar/ranlib/pkg-config/ninja 绝对路径
- `_build_environment()` PATH 前置 wrapper 目录与依赖 bin
- ninja 探测兜底：`NINJA` 环境变量（meson 支持）——本配方通过 machine
  file `ninja = '<abs>'` 覆盖

### 4. gettext msgfmt ITS 规则

`i18n.merge_file(type:'desktop'/'xml')` → msgfmt 需要 ITS 规则。
hnp gettext 0.26 的 ITS 在
`/data/service/hnp/gettext.org/gettext_0.26/share/gettext-0.26/its`，
但 msgfmt 只在 `$XDG_DATA_DIRS/gettext/its` 搜索 → 构建时设
`XDG_DATA_DIRS=<staging share>` 并在其中放置 ITS 文件 + hicolor
index.theme + GTK schemas（见下）。hnp msgfmt 本身可用（0.26）。

### 5. GTK 3.24.43 icon theme brk 断言（上游库缺陷规避）

无 hicolor icon theme 时 `gtk_icon_theme_lookup_icon` 打印 warning 后
走 brk 断言（musl 无断言消息直接 SIGTRAP；最小复现：lookup 任意不存
在图标）。glade 的 `glade_init()→register_icon_names()` 必触发。
规避：测试/运行环境提供最小合法 hicolor index.theme（本配方
`_write_test_runtime_data()` staging 到 `test-data/share`）。带合法
theme 后 lookup 正常返回 NULL。

### 6. broadway 虚拟显示（上游测试运行机制）

GTK broadway 后端的 display 协议（读源码 gdkbroadway-server.c +
broadwayd.c 实证）：
- `BROADWAY_DISPLAY=:tcpN`（**不是 DISPLAY！** gtk_init_check→
  gdk_display_open_default 传 NULL 时读 BROADWAY_DISPLAY；设 DISPLAY
  会导致 broadway 走 abstract unix socket 路径失败）→ TCP 127.0.0.1:
  9090+N
- broadwayd 启动：`broadwayd :tcp5`（监听 9095 裸协议端口 + 8085 http）
- broadwayd 是 gtk 包内 OHOS ELF → staging + 重签名（同 glib 工具）
- `GDK_BACKEND=broadway` 必须设置
- broadwayd 需 `setsid` 启动，否则 conan build 结束时被进程组信号杀掉

### 7. 测试环境完整变量集（实测通过组合）

```
BROADWAY_DISPLAY=:tcp5
GDK_BACKEND=broadway
XDG_DATA_DIRS=<staging>/share   # hicolor index.theme + glib schemas + gettext ITS
GLADE_TESTING=1
GLADE_CATALOG_SEARCH_PATH=<src>/plugins/gtk+
GLADE_MODULE_SEARCH_PATH=<build>/plugins/gtk+
GLADE_PIXMAP_DIR=<src>/data/icons
GLADE_ICON_THEME_PATH=<src>/plugins/gtk+/icons/22x22
LD_LIBRARY_PATH=/system/lib64:<SDK llvm lib>:<conan 依赖 lib>:<build>/gladeui
```

FileChooserButton 用例需要 org.gtk.Settings.FileChooser schema（gtk 包
share/glib-2.0/schemas 带 xml，glib-compile-schemas 编译后放
XDG_DATA_DIRS）。/system/lib64 提供 libc++_shared.so（harfbuzz 需要）。

### 8. 上游测试结果（2026-09-03 实测）

| 套件 | 结果 |
|---|---|
| add-child | **1228/1228 PASS** |
| create-widgets | **154/154 PASS** |
| refcount | **1/1 PASS** |
| toplevel-order | **7/7 PASS** |
| modules | 0/2（python/gjs plugin 缺失，环境限制跳过） |

计 1390 通过 / 0 失败 / 2 跳过（跳过原因：pygobject/gjs 生态在 OHOS
制品仓不存在，meson 已 disable，非适配缺陷）。

### 9. ELF 签名

package() 后对 bin/* 与 lib/*.so* 全部 selfSign（ci/artifacts/sign.sh
同款流程），未签名 OHOS ELF 无法在设备上执行。

## 已知限制

- python/gjs/webkit2gtk 部件目录未构建（生态缺失，上游 meson 可选特性）
- help/（yelp 文档）未构建（itstool 缺失，运行时可选数据）
- meson_post_install.py 的 gtk-update-icon-cache 在 DESTDIR 语义下跳过
  （图标缓存为运行时可再生资源，不阻塞）

## 排错索引

- 链接 `g_libintl_*` undefined → glib-2.0.pc 补 -lintl（见 2）
- meson `Could not get pkg-config variable` → 对应 pc 补工具变量（见 2）
- 测试 SIGTRAP (rc=133) 无消息 → 检查 XDG_DATA_DIRS 是否含 hicolor
  index.theme（见 5）
- 测试 "cannot open display" → 用 BROADWAY_DISPLAY 而非 DISPLAY；
  确认 broadwayd :tcp5 存活（见 6）
- "No GSettings schemas are installed" → staging schemas 未编译/未进
  XDG_DATA_DIRS（见 7）
## 对话记录（适配过程摘要）

- 2026-09-03 18:24 任务启动（calbee21 积分赛，平台 taskBranch
  feat/glade-3.40.0-r9-H036-clean）
- W1 同步 main（f5131ee224）；W0 依赖实测（gtk/3.24.43、
  libxml2/2.15.3、pango/1.50.14.1、gdk-pixbuf/2.44.6 全部 ohpcd
  可下载）
- lang-preflight: c（218 源文件 c:215, 99%）→ 匹配 cpp 兼容族
- 探索性构建 ~/tmp/glade-explore：meson 315 目标全通；期间定位并
  解决 8 个平台适配点（见上"关键适配点"）
- 上游测试：broadwayd :tcp5 下 4/5 套件 1390 用例全过；modules 需
  python/gjs plugin（生态缺失跳过）
- conan create 迭代 13 轮：pc 修补 → XDG/ITS → image-missing →
  test_package broadwayd LD_LIBRARY_PATH → pixmaps/模块路径 →
  ELF 双签（HMFS 首签失效规避）→ 全绿
- finish published：W3 本地 CI 模拟通过（.ci-result.json
  integrity_hash cd25c1864f7e8359）
---

**编译结束**: 2026-09-03 20:05
**最终状态**: published
