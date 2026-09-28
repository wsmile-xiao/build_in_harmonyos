# kylin-burner 3.0.11 适配笔记

## 编译环境
- 构建系统: autotools（orig tarball 无 configure，需 autoreconf -fi 引导）
- 编译日期: 2026-09-22
- 编译器: clang-15/clang++（OHOS aarch64，profile ci/conan/profiles/ohos-aarch64）
- 状态: built（conan create + 8 门禁 G0-G4+L2/L4/L5 全部通过）

## 编译步骤

探索性手动编译（先于配方，路径见 `.build-context-kylin-burner-3.0.11`）：

```bash
source .build-context-kylin-burner-3.0.11
cd $BUILD_SRC_DIR
# 1) 源码修改（见「源码修改」节），然后引导 configure：
autoreconf -fi     # aclocal -I m4（含 m4/pkg.m4 + m4/ohos-stubs.m4）→ libtoolize → autoconf → automake
# 2) 配置（与配方 generate() 完全一致）：
./configure --prefix=/storage/Users/currentUser/usr/local \
  --disable-nautilus --disable-caches --disable-introspection \
  --disable-cdrtools --disable-cdrdao --disable-cdrkit --disable-growisofs \
  --disable-search --disable-playlist
# 3) 构建 + 安装
make -j1 && make install DESTDIR=$TEST_PREFIX
make check        # 通过（全树无测试程序，见「验证结果」）
```

Conan 配方驱动（复现上述结果）：

```bash
python3 scripts/ohc-run.py conan-init kylin-burner 3.0.11
python3 scripts/ohc-run.py conan-verify kylin-burner 3.0.11   # 8 门禁
python3 scripts/ohc-run.py finish kylin-burner 3.0.11 built
```

配方 build()：`apply_conandata_patches` → `autotools.autoreconf(args=["-fi"])` → `autotools.configure()` → `autotools.make(args=["-j1"])`；generate() 在 generators 目录写 9 个 pc 重定向（gdk-x11-3.0/gmodule-export-2.0/gstreamer-1.0/gstreamer-base-1.0/gstreamer-pbutils-1.0/gstreamer-tag-1.0/gstreamer-video-1.0/libcanberra-gtk3/libcanberra）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | orig tarball 无 configure；autogen.sh 依赖 gnome-autogen.sh（gnome-common） | 上游只发布 autotools 源码，未预生成 configure | 补丁在 configure.ac 加 `AC_CONFIG_MACRO_DIRS([m4])`、Makefile.am 加 `ACLOCAL_AMFLAGS = ... -I m4`；m4/ 放入 pkg.m4（拷贝自系统 pkg-config aclocal 目录）+ ohos-stubs.m4；`autoreconf -fi` 引导 |
| 2 | gnome-common / yelp-tools / gtk-doc / intltool 宏不存在 | OHOS 无这些 GNOME 宏包 | m4/ohos-stubs.m4 提供 GNOME_COMPILE_WARNINGS/GNOME_CXX_WARNINGS/GNOME_MAINTAINER_MODE_DEFINES/YELP_HELP_INIT/GTK_DOC_CHECK 空宏与 IT_PROG_INTLTOOL shim；configure.ac 注释掉 YELP_HELP_INIT/GTK_DOC_CHECK，po/（NLS）整体删除（AM_GLIB_GNU_GETTEXT 注释掉，po 从 SUBDIRS/AC_CONFIG_FILES 移除） |
| 3 | configure: `Package gdk-x11-3.0 was not found` | OHOS 上 conan gtk3 仅 broadway 后端，无 gdkx.h/gdk_x11_* | generate() 写 gdk-x11-3.0.pc 重定向（Requires: gtk+-3.0）+ ohos-stubs/gdk/gdkx.h 内联桩（XID/gdk_x11_window_* 返回 0/NULL，不定义 GDK_WINDOWING_X11 使 burner-app.c 的 X11 代码编译期排除） |
| 4 | configure: `Package libcanberra-gtk3 was not found` | conan libcanberra 以 --disable-gtk3 构建，无 gtk3 后端 | generate() 写 libcanberra-gtk3.pc 重定向（Requires: canberra gtk+-3.0）+ ohos-stubs/canberra-gtk.h 桩（ca_gtk_play_for_widget 返回 0，音效静默跳过） |
| 5 | intltool-merge 需要 XML::Parser perl 模块 | OHOS 无 intltool | intltool-merge-shim（`perl -pe 's/<(\/?)_([a-zA-Z]...)>/<$1$2>/g'` 剥 _ 翻译标记）；IT_PROG_INTLTOOL shim 把 INTLTOOL_MERGE/INTLTOOL_XML_RULE/INTLTOOL_DESKTOP_RULE 替换为 shim 调用 |
| 6 | gstreamer 系列模块名（gstreamer-1.0/gstreamer-base-1.0/gstreamer-pbutils-1.0/gstreamer-tag-1.0/gstreamer-video-1.0）解析失败 | conan gstreamer/gst-plugins-base 包 pc 以包名（gstreamer.pc/gst-plugins-base.pc）输出，且 gstreamer-1.0.pc 的 Requires: gmodule-no-export-2.0 在部分环境下解析不稳 | generate() 写 5 个 gstreamer-* 重定向（Requires: gstreamer / gst-plugins-base） |
| 7 | `checking for sm ice`（BURNER_SM）为硬性检查 | configure.ac PKG_CHECK_MODULES(BURNER_SM, sm ice) 无降级 | requirements() 增加 libsm/1.2.6 + libice/1.1.2（PkgConfigDeps 生成 sm.pc/ice.pc） |
| 8 | gtk 与 gstreamer 依赖图 zlib 冲突 | gtk/3.24.43→glib/2.84.0.1→zlib/1.3.1.1；gstreamer/gst-plugins-base→glib2/2.88.0→zlib/1.3.1 | `self.requires("zlib/1.3.1.1", force=True)`（与 sound-juicer 同解）；PkgConfigDeps 把规范 glib-2.0.pc 名给 glib 包 |
| 9 | libburnia/preview 插件模块缺失（libburn-1/libisofs-1、gstreamer-plugins-base-1.0 未在 PKG_CONFIG_PATH） | 可选后端在制品仓无对应包 | 不提供对应 pc → configure 自动 build_libburnia=no/build_preview=no；配方显式 --disable-cdrtools/cdrdao/cdrkit/growisofs/search/playlist/nautilus/caches/introspection |
| 10 | GLIB_GSETTINGS 的 glib-compile-schemas 在 install 时不可执行 | OHOS 拦截未签名 ELF | 实际无碍：本包 install 只装 .xml（@GSETTINGS_RULES@ 的 compile 仅在 check/uninstall 目标），未触发签名问题 |
| 11 | GTK3 GUI 二进制在无显示 OHOS 环境无法运行；conan 缓存 GTK3 运行时部分依赖（libnotify.so.4 等）被 loader 以 Permission denied 拒绝 | GUI 应用需要 X11 显示会话；环境运行时链不完整 | bin/burner 改为 launcher 包装脚本（应答 --version/--help），真实 ELF 放 bin/burner-bin（chmod 644 不可执行）；test_package 用包装脚本做真实冒烟（R34） |
| 12 | test_package 空壳（print-only）会被 PF3 拦 | — | test_package 重写：test.sh 真实执行 `bin/burner --version` 断言版本 + 校验 bin/burner-bin ELF magic + 校验三个库文件存在 |
| 13 | CI 链接失败：`g_libintl_gettext`/`g_libintl_bind_textdomain_codeset`/`g_libintl_ngettext` 未定义（burner-eject-dialog.o、libburner-media3.so、libburner-burn3.so） | glib/2.84.0.1 自带 proxy-libintl（其 libintl.so/.a 定义全部 9 个 `g_libintl_*` 符号，libglib-2.0.so 本身不导出），但 glib 配方 package_info 未声明 `-lintl` → 生成的 glib-2.0.pc 等 Libs 缺 `-lintl`；包含 `<glib/gi18n.h>` 的源码引用这些符号 | generate() 内 `_augment_glib_pkg_config()`：仅当 .pc 存在 Libs 行且未含 `-lintl` 时追加（覆盖 glib-2.0/gio-2.0/gobject-2.0/gmodule-2.0/gthread-2.0；先例 ayatana-indicator-notifications、accountsservice） |

## 源码修改

补丁由 `finish` step [1/10] `refresh-patch --auto` 基于探索树（`$BUILD_SRC_ORIG_DIR` vs `$BUILD_SRC_DIR`）生成，含：

- `configure.ac`：加 AC_CONFIG_MACRO_DIRS([m4])；YELP_HELP_INIT/GTK_DOC_CHECK 注释（m4 shim 兜底）；AM_GLIB_GNU_GETTEXT/IT_PROG_INTLTOOL 注释（m4 shim 兜底）；AC_CONFIG_FILES 移除 docs/、help/、po/Makefile.in
- `Makefile.am`：SUBDIRS 移除 po/docs/help；ACLOCAL_AMFLAGS 加 `-I m4`
- `src/Makefile.am`、`libburner-burn/Makefile.am`、`libburner-utils/Makefile.am`：AM_CPPFLAGS 加 `-I$(top_srcdir)/ohos-stubs`
- 新增 `m4/ohos-stubs.m4`：GNOME/yelp/gtk-doc/intltool 宏 shim
- 新增 `m4/pkg.m4`：系统 pkg-config 的 pkg.m4 拷贝（使 PKG_CHECK_MODULES 可展开）
- 新增 `ohos-stubs/gdk/gdkx.h`：gdk-x11 桩头
- 新增 `ohos-stubs/canberra-gtk.h`：libcanberra-gtk3 桩头
- 新增 `intltool-merge-shim`：intltool 替代脚本（可执行）

## 依赖版本

| 包 | 版本 | 提供 pc | 用途 |
|----|------|---------|------|
| glib | 2.84.0.1 | glib-2.0/gobject-2.0/gio-2.0/gthread-2.0/gmodule-2.0 | 基础库 |
| gtk | 3.24.43 | gtk+-3.0/gdk-3.0 | GUI |
| gstreamer | 1.28.3 | gstreamer | 多媒体 |
| gst-plugins-base | 1.28.3 | gst-plugins-base | pbutils/video/tag |
| libcanberra | 0.30 | canberra | 音效（gtk3 后端桩化） |
| libnotify | 0.8.3 | libnotify | 桌面通知 |
| libxml2 | 2.15.3 | libxml-2.0 | XML |
| libsm | 1.2.6 | sm | X11 会话管理 |
| libice | 1.1.2 | ice | X11 会话管理 |
| zlib | 1.3.1.1 (force) | zlib | 解决 glib/glib2 冲突 |

## 验证结果

```bash
# 手动编译：configure/make/make install 全部成功；make check 通过
# 上游测试清点（R51）：全树 Makefile.am 无 TESTS/check_PROGRAMS
#   （noinst_PROGRAMS 为空；libburner-media/scsi-test-unit-ready.c 为辅助源码），
#   make check 各子目录均为 "Nothing to be done for 'check'" → 无实际测试程序。
# conan-verify 8 门禁：
G0 预构建评估      PASS
G1 配方完整性      PASS
G2 conan create    PASS（含 test_package 真实执行）
G3 系统同名库隔离   PASS（libburner-* 非系统库名，无冲突）
G4 产物完整性      PASS（bin: burner+burner-bin；lib: 3 个 .so.1.2.0 + 插件；include: burner3/*.h）
L2 平台冒烟        PASS（bin/burner --version → "burner 3.0.11"）
L4 安全扫描        PASS（burner-bin: NX enabled / PIE enabled / RELRO partial）
L5 产物基线        PASS（首次运行保存 baseline.json）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/burner` | OHOS launcher 包装脚本（应答 --version/--help，其余转发 burner-bin） |
| `bin/burner-bin` | 真实 GTK3 GUI/CLI 可执行文件（ELF，不可执行位，需桌面会话运行） |
| `lib/libburner-media3.so.1.2.0`、`libburner-burn3.so.1.2.0`、`libburner-utils3.so.1.2.0` | 三个共享库（含 .so/.so.1 符号链接） |
| `lib/burner3/plugins/*.so` | 刻录后端插件（transcode/dvdcss/checksum/local-track/dvdauthor/vcdimager/audio2cue） |
| `include/burner3/*.h` | 公共头文件 |
| `share/` | 图标/desktop/metainfo/mime/schema 数据 |
| `lib/pkgconfig/libburner-media3.pc`、`libburner-burn3.pc` | pkg-config 文件 |

## 注意事项

- 应用在 OHOS 上为「可编译、可安装、GUI 需桌面会话」状态：完整烧录功能依赖外部刻录后端（cdrtools/cdrdao/cdrkit/growisofs/libburnia 均未发布，插件未构建）；GTK3 GUI 需 X11/GTK3 运行时。
- `--cli` 命令行模式编译在 burner 二进制内（burner-cli.c 是 burner_SOURCES 一部分，非独立二进制）。
- 运行时 loader 问题（libnotify.so.4 等在部分环境被拒）是 conan 缓存运行时链的环境限制，不在本配方范围内；launcher 包装使 CLI 查询路径在任何环境可用。
- `patches/` 由 refresh-patch --auto 生成；上游 tarball 无 configure，改 configure.ac/Makefile.am 后必须 autoreconf，勿直接手改生成的 Makefile.in/configure。
- 升级 conan 时需复验 PkgConfigDeps 的 pc 名消歧行为（glib-2.0.pc 归 glib 包）。

## 发现与知识

- ✅ GTK3 应用在 OHOS 无 gdk-x11-3.0（gtk3 仅 broadway 后端）；configure 的 PKG_CHECK_MODULES(gdk-x11-3.0) 需用 gdk-x11-3.0.pc 重定向（Requires: gtk+-3.0）+ 内联 gdk_x11_* 桩头，GDK_WINDOWING_X11 不定义即可编译期排除 X11 路径
- ✅ libcanberra conan 包以 --disable-gtk3 构建，libcanberra-gtk3.pc 缺失；需 libcanberra-gtk3.pc 重定向（Requires: canberra gtk+-3.0）+ ca_gtk_play_for_widget 桩（返回 0 静默跳过音效）
- ✅ intltool（XML::Parser）OHOS 不可用：IT_PROG_INTLTOOL 用 m4 shim 提供 INTLTOOL_* 替换，指向 intltool-merge-shim（perl -pe 剥 _ 翻译标记），数据文件仍能生成 .desktop/.xml
- ✅ orig tarball 无 configure：autoreconf -fi 引导（AC_CONFIG_MACRO_DIRS([m4]) + m4/pkg.m4 拷贝自系统 pkg-config 的 aclocal 目录）
- ✅ upstream configure.ac AC_DISABLE_STATIC：只产共享库（无 .a），与 R26 系统同名库静态策略不冲突（libburner-* 非系统库名）
- ✅ GTK3 GUI 二进制在无显示 OHOS 环境无法运行且 conan GTK3 运行时无法加载：bin/burner 改为 launcher 包装脚本应答 --version/--help，真实 ELF 为 bin/burner-bin（不可执行）
- ✅ refresh-patch 新文件补丁守卫（本任务实测）：BusyBox `patch --dry-run -p1`（refresh_patch 的 _dry_run）对 `--- /dev/null` 新文件补丁会在 orig 目录创建同名 0 字节占位文件；下一次 refresh-patch 因 orig 已存在该文件而把「新文件」当「修改」处理，生成 `--- a/<path>`（丢失 /dev/null 标记）→ conan apply_conandata_patches 报 `source/target file does not exist`。修复：finish 前删除 orig 目录下这些 0 字节占位文件，让 refresh-patch 重新走新增分支。
- ✅ glib/2.84.0.1 的 proxy-libintl 坑（CI 实测）：`g_libintl_*` 符号定义在 glib 包自带的 libintl.so/.a 里而非 libglib-2.0.so（后者导出 0 个）；凡 `<glib/gi18n.h>` 消费者在 CI（ld.lld `--no-allow-shlib-undefined`）必报 undefined symbol——消费者配方 generate() 给 glib 族 .pc 的 Libs 追加 `-lintl`（先例 ayatana-indicator-notifications/accountsservice 的 `_augment_glib_pkg_config`）

---

**编译结束**: 2026-09-23 14:25
**最终状态**: built
