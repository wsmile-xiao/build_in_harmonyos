# marco 1.26.2 适配笔记

## 概述

MATE 窗口管理器（X11 合成窗口管理器，GTK 3）。产物：`bin/marco`、
`bin/marco-message`、`bin/marco-window-demo`、`bin/marco-theme-viewer`、
`lib/libmarco-private.so.2.0.0`、`include/marco-1/marco/*.h`、
`share/glib-2.0/schemas/org.mate.marco.gschema.xml`、112 个语言的 mo 文件。

- 构建系统：autotools（release tarball 自带 configure / Makefile.in）
- 编译日期：2026-09-13
- 编译器：OpenHarmony Clang 15.0.4（aarch64-linux-ohos）
- 状态：built（W3 本地 conan create 通过，含 test_package 99 条断言）

## 上游测试清点（R51 三步法）

**上游测试完整清单 = 8 个程序 / 21 个用例**（rule4 口径：声明数须 ≥ 实测数；
下表为可审计的逐项枚举，覆盖"仅数 meson test()"（=5）与"数 noinst 程序"（=8）
两种实测口径）。

### 第 1 步：清点

| 类别 | 用例数 | 来源 | 注册方式 |
|------|--------|------|----------|
| 单元测试（自检程序） | **14** | `src/core/testboxes.c` 的 14 个 `test_*` 用例（73 条 `g_assert`） | `src/Makefile.am:146 noinst_PROGRAMS`（**未**注册为 meson test()/autotools TESTS） |
| 集成测试（meson 注册的交互式程序） | **5** | `src/wm-tester/meson.build:61-65` 的 5 条 `test()`（全仓 meson.build 仅此 5 条 test() 注册） | meson `test()` |
| 其他测试（未注册的演示程序） | **2** | `src/ui/testgradient.c`、`src/core/testasyncgetprop.c` | `src/Makefile.am:146 noinst_PROGRAMS` |
| **合计** | **21** | | |

autotools 路径（本适配使用）无 `TESTS`/`check_PROGRAMS`/`check-local`，`make check`
仅递归 po/src/themes 并报 "Nothing to be done for 'check'"（0 用例）。

### 第 2 步：可运行环境实际运行

`make all` 会构建上述全部 noinst 程序，故可直接实测（构建目录 + 包目录取自
同一次 `conan create`）：

```bash
LD_LIBRARY_PATH=<build>/marco-libdir \
  timeout 30 <build>/src/<name> </dev/null; echo rc=$?     # testboxes / testgradient / testasyncgetprop
LD_LIBRARY_PATH=<build>/marco-libdir \
  timeout 30 <build>/src/wm-tester/<name> </dev/null; echo rc=$?   # meson 注册的 5 项
```

| # | 上游程序 | 用例数 | 实测 | 具体技术原因与报错定位 |
|---|----------|--------|------|------------------------|
| 1 | `testboxes` | **14** | **rc=0，14/14 通过**（每个用例打印 `<name> passed.`，末行 `All tests passed.`） | 纯几何自检、**不依赖 X display** → 本环境下唯一可真实运行的上游用例集；已由配方 `build()` 内 `_run_upstream_self_tests()` 纳入门禁（用例数 ≠ 14 或缺少 `All tests passed.` 即构建失败） |
| 2 | `wm-tester` | 1 | rc=1，无 stdout | `main.c:40 gtk_init()` 取不到显示后端：stderr `(wm-tester:PID): Gtk-WARNING **: cannot open display:`。本平台 GTK（制品仓 gtk/3.24.43）只含 broadway 后端、设备无 X server/X socket → GTK 显示初始化必然失败；该程序是人工驱动的交互式工具（`--evil`/`--icon-windows` + GTK 主循环），无断言、无自动判定 |
| 3 | `test-gravity` | 1 | rc=139（SIGSEGV） | `test-gravity.c:130 d = XOpenDisplay(NULL)` 在无 X server 时返回 NULL，紧接 `:131 screen = DefaultScreen(d)`（及 `:132-133 DisplayWidth/Height(d,…)`）解引用 NULL → 段错误。属上游交互式演示程序面向真实 X server 的既有假设，非本适配引入（该路径不经 X11 兼容层） |
| 4 | `test-resizing` | 1 | rc=139（SIGSEGV） | 同 #3：`test-resizing.c:104 XOpenDisplay(NULL)` → NULL，`:106 DefaultScreen(d)` 解引用 |
| 5 | `focus-window` | 1 | rc=1，`Usage: focus-window WINDOWID` | `focus-window.c:13-15` 要求 WINDOWID 入参；它是其它演示/人工验证的辅助工具（聚焦指定窗口），无独立自动判定，`:19` 亦走 `XOpenDisplay(NULL)` |
| 6 | `test-size-hints` | 1 | rc=139（SIGSEGV） | 同 #3：`test-size-hints.c:50 XOpenDisplay(NULL)` → NULL，`:52 DefaultScreen(d)` 解引用 |
| 7 | `testgradient` | 1 | rc=1，`Gtk-WARNING **: cannot open display:` | 交互式演示程序，需 GTK 显示后端（本平台 GTK 仅 broadway、设备无 X server） |
| 8 | `testasyncgetprop` | 1 | rc=1，`specify window ID` | 需外部入参（窗口 ID）与活动 X display 的手动诊断工具，无独立自动判定 |

**通过率：14/21 用例（66.7%）**；其中**在本环境可运行的 14 项全部通过（14/14 = 100%）**，
即上游自检用例集 `testboxes` 已被纳入 `build()` 门禁；其余 7 项均依赖**活动
X display**（1 项要 GTK 显示后端、3 项直接 `XOpenDisplay(NULL)` 后解引用、2 项需
外部入参、1 项需 GTK 显示），HarmonyOS PC 当前无 X server / X socket，`Xvfb` 类
服务器与本仓制品仓均无可用二进制（`xorg-server` 仅存在于源码归档、registry 无
binary）→ 属**环境限制**，已逐项给出实测 rc 与源码行级报错定位。

### 第 3 步：如实回填

- PR 描述「测试用例对比」表：上游 **N=21**（单元 14 + 集成 5 + 其他 2）；
  验证结果：上游 **14/21（66.7%）**，可运行项 **14/14 = 100%**，不可运行 7 项逐项技术原因。
- `test_package/MANIFEST.yml`：`upstream_test_count: 21`（含 breakdown 与
  meson 注册口径 5 的对照）、`upstream_tests` 8 个程序逐条 `measured`/`technical_reason`、
  `upstream_test_pass_rate`。
- 若后续提供 X server（或在真机桌面会话内），上表命令可直接复跑其余 7 项。

## 适配实现（5 个补丁）

| 补丁 | 内容 | 触发问题 |
|------|------|----------|
| 0001-gdk-x11-compat | 新增 `src/x11-compat/gdk/gdkx.h` + `src/x11-compat/marco-x11-compat.c` | 制品仓 gtk/3.24.43 是 broadway 后端：无 `gdk/gdkx.h`、无 `gdk_x11_*` 符号；marco 是纯 X11 客户端（11 个文件包含 gdkx.h、`GDK_DISPLAY_XDISPLAY` 100 处、`GDK_WINDOW_XID` 13 处） |
| 0002-canberra-gtk3-shim | 新增 `src/x11-compat/canberra-gtk.h`（`ca_gtk_context_get()`） | `MARCO_PC_MODULES` 无条件要求 `libcanberra-gtk3`，制品仓 libcanberra/0.30 用 `--disable-gtk3` 构建 |
| 0003-config-guess-sub | config.guess 增加 HarmonyOS uname 分支；config.sub 接受 ohos OS/内核组合 | 2023 年 config.guess 走编译器探针（OHOS 拒绝 exec 未签名探针二进制）→ "cannot guess build type"；config.sub 不识别 `aarch64-linux-ohos` |
| 0004-zenity-optional | zenity 检查 `AC_MSG_ERROR` → `AC_MSG_WARN` | 制品仓未发布 zenity；zenity 是运行时可选对话框助手（`src/core/util.c` 按名字查找） |
| 0005-cairo-xlib-compat | 新增 `src/x11-compat/cairo-xlib.h`、`cairo/cairo-xlib.h`、`marco-cairo-xlib.c` | 制品仓 cairo/1.18.4 为 xlib=disabled（无 `cairo_xlib_*` 符号与 `cairo-xlib.h`）；窗口边框渲染与 xrender 合成器需要 X pixmap → cairo surface |

### 兼容层设计（0001 / 0005）

与仓库先例 `libwnck3/43.3` 的 x11-compat 同构：单例 `XOpenDisplay` 连接
（`GMutex` 保护）、window↔XID 双向 `GHashTable`（未命中时在 root 上建 1x1
窗口并选择事件掩码）、`XSetErrorHandler` 错误陷阱、16ms `GSource` 分发
`gdk_window_add_filter` 注册的过滤器。marco 特有的语义修正：
`gdk_x11_lookup_xdisplay()` 必须返回 `gdk_display_get_default()`
（`src/ui/ui.c:271/273` 有 `g_assert`），故不是简单指针强转。

Cairo-Xlib 侧用 `XGetImage` 取像素后包成 cairo image surface（`CAIRO_FORMAT_RGB24`
/ `CAIRO_FORMAT_A8`），`cairo_xlib_surface_get_width/height` 直接读 image surface
尺寸。无 X server 时所有入口安全降级（返回 NULL/None/0），不崩溃。

### 构建接入（不改生成文件的取舍）

兼容层的两个 `.c` 不加入 `src/Makefile.am`（那需要 automake 重生成
`Makefile.in`；本机与 CI 都没有 automake/libtool 全链，`/data/service/hnp/bin`
只有 autoconf 家族）。配方在 `build()` 里用工具链变量编译兼容层为目标文件，
经 `make LIBS="..."` 追加到每条链接命令末尾；头目录经
`AutotoolsToolchain.extra_cflags` 置于依赖头之前（使 `<gdk/gdkx.h>`、
`<cairo/cairo-xlib.h>`、`<canberra-gtk.h>` 命中兼容层版本）。R6 意义上
补丁只新增源文件，没有改动任何生成文件。

## 遇到的问题与解决方案

| # | 现象 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 报 "Missing prebuilt package for gtk/3.24.43"，随后 GTK 源码重建失败（meson 127） | 本机 `~/.conan2` 存在在研实验 revision（cairo 1.18.4 加 libx11、cairo-gobject 1.18.4.2、libepoxy 1.5.10 GLX、gtk 3.24.52 x11），使 gtk 的 embed 依赖信息漂移 → package_id 与制品仓二进制失配 | 用干净 CONAN_HOME（新目录 + 仅 ohpcd remote）解析：41 节点依赖图 0 Missing，全部走预编译 binary；本仓 CI 使用干净 worker 缓存，不受本机实验 revision 影响 |
| 2 | `configure: error: cannot guess build type` | config.guess 走编译器探针，OHOS 拒绝 exec 未签名探针 ELF | 补丁 0003（uname → `aarch64-unknown-linux-ohos`） |
| 3 | `configure: error: glib-compile-schemas not found` | `GLIB_GSETTINGS` 用 `pkg-config --variable=glib_compile_schemas gio-2.0`，PkgConfigDeps 生成的最小 .pc 无该变量 | 配方把变量插入生成的 gio-2.0.pc（指向自签的 glib-compile-schemas 副本） |
| 4 | `configure: error: gdk-pixbuf-csource executable not found` | 构建期需要 gdk-pixbuf 的自带工具，host 依赖 bin 不在 build PATH | 配方从 gdk-pixbuf 包复制该工具并 `binary-sign-tool` 自签（OHOS 拒绝执行未签名 ELF） |
| 5 | `configure: error: zenity not found` | 制品仓未发布 zenity | 补丁 0004 + 配方对生成物 configure 的同源机械替换（改为警告） |
| 6 | `configure: error: itstool not found` | `YELP_HELP_INIT` 强制检查 itstool（帮助文档翻译构建） | `tool_requires("itstool/2.0.7")`（制品仓已发布） |
| 7 | `config.status: error: could not setup config files machinery`（`can't create ./confXXXXXX/subs1.awk: Permission denied`） | HMDFS 上玩具 `mktemp -d` 生成的目录是 2700（chmod 被文件系统忽略、group 位不可恢复）→ 目录内不能创建文件；而 configure 自带的 mkdir 回退分支产生的目录被归一化为 2771，可写 | 配方把 configure 里 `mktemp -d` 分支改为直接走 mkdir 回退（同源机械替换，匹配不到即报错） |
| 8 | `AC_CHECK_LIB(Xext/Xrandr/Xinerama/SM...)` 全部 "no"（静默裁掉窗口管理能力） | 依赖的 -L/-I 不在 configure 的搜索路径（PkgConfigDeps 只提供 .pc 变量） | `AutotoolsToolchain.extra_ldflags/extra_cflags` 注入依赖 libdir/includedir（探测结果恢复为 yes） |
| 9 | libtool `cannot find the library .../libxcb.la` | 制品仓 X11 包的 `.la` 记录了打包机绝对路径（`~/.cache/conan2/...`、`~/.conan2/p/b/...`，均不存在） | 配方建立 build_folder 私有 `.so` 副本目录并置于 `-L` 首位，libtool 找不到 .la 即直接用 .so（R49；cairo-gobject 的 libcairo.so 最后覆盖以胜出同 SONAME） |
| 10 | `undefined symbol: g_libintl_gettext` | PkgConfigDeps 生成的 glib-2.0.pc 丢了本仓 glib 的 `-lintl`（`g_libintl_*` 由包内 libintl.so 提供） | 配方给生成的 glib-2.0.pc 的 Libs 追加 `-lintl`（libwnck3/43.3 同款） |
| 11 | `cairo/cairo-xlib.h: No such file or directory` | 制品仓 cairo 为 xlib=disabled | 补丁 0005 兼容层（不换 cairo-gobject/1.18.4.3：那会把 libx11/libxrender 带进 gtk 的 embed 信息，使 gtk 预编译 binary 失配） |
| 12 | `undefined symbol: ca_context_create` | 兼容层调用 libcanberra，而 marco-message / marco-window-demo 的 LIBS 不含 canberra | `make LIBS` 追加 `-L<libcanberra>/lib -lcanberra`（make 命令行变量需整体加引号，否则空格被当作 make 选项） |
| 13 | test_package 的 `no_display_guard` 断言 `gdk_x11_screen_get_number` 存在失败 | 该符号不是 marco 使用的 GDK-X11 入口（真名 `gdk_x11_screen_get_screen_number`） | 修正测试断言为真实符号名 |

## 依赖版本

gtk/3.24.43、glib/2.84.0.1、cairo/1.18.4、cairo-gobject/1.18.4.2、
pango/1.50.14.1.1、gdk-pixbuf/2.44.6.1、atk/2.38.0.1.1、libcanberra/0.30、
libx11/6.4.0（override）、libxext/6.4.0、libxrender/0.9.12、libxrandr/1.5.5、
libxcursor/1.2.3、libxinerama/1.1.6、libxdamage/1.1.6.1、libxcomposite/0.4.6、
libxfixes/6.1.0、libxres/1.2.1、libice/1.1.2、libsm/1.2.6；
overrides：pixman/0.46.4、libjpeg-turbo/3.2.0、fontconfig/2.18.1.1、
expat/2.8.2.1；tool_requires：itstool/2.0.7。

## 验证结果

- 官方源码 SHA-256：通过（`12f1a254fe1072f0304884711e089a5682780a011593402ed38de6b9480e07a3`）
- `conan create`（ohos-aarch64 profile，host/build 同 profile）：通过
- `make check`：执行（autotools 路径 0 用例，日志留痕）
- 上游自检测试：`testboxes` 14/14 用例通过（rc=0，`All tests passed.`），由
  `build()` 内 `_run_upstream_self_tests()` 真实执行并纳入门禁
- test_package：99 条断言全通过（几何契约 60、符号/类型 24、无 X 降级 12、
  `marco --version/--help/未知选项` 3），`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...}`
- 运行期限制：marco 是 X11 窗口管理器，运行需要 X server（鸿蒙 PC 目前没有），
  本适配保证"可编译、可加载、行级契约可测、无 X 时安全降级"

详细命令与输出摘要见 `reports/test-report.md`。

## 交付物

- `bin/marco`、`bin/marco-message`、`bin/marco-window-demo`、`bin/marco-theme-viewer`
- `lib/libmarco-private.so.2.0.0` 及 SONAME 链接、`lib/pkgconfig/libmarco-private.pc`
- `include/marco-1/marco/*.h`
- `share/glib-2.0/schemas/org.mate.marco.gschema.xml`、`share/applications/marco*.desktop`、
  `share/locale/*/LC_MESSAGES/marco.mo`、man 手册

COMPLETED — marco 1.26.2 适配完成，状态: built
---

**编译结束**: 2026-09-13 23:14
**最终状态**: built（未 upload，upload 发生在合并后）
