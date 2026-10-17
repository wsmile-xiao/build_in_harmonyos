# gtksourceview4 4.8.4 适配笔记

## 编译环境
- 构建系统: meson（4.8.4 上游 meson_version >= 0.50.0，c_std=gnu99）
- 编译日期: 2026-09-28
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链，target aarch64-unknown-linux-ohos）
- 依赖: gtk/3.24.43（OHOS shared 发布二进制）、libxml2/2.15.3、fribidi/1.0.16
- 状态: 配方 + test_package 就绪；本机 ohpcd 远程被网关拦（system acceleration
  policy not enabled）且本地 conan 缓存缺 cairo/pixman/gtk 二进制，故**本机未跑
  conan create**，实编与用例结果以 CI（同配方同 profile）为准（如实申报）。

## 背景

GtkSourceView 4 是 GNOME 的语法高亮文本组件库，**4.x 线仍是 GTK3 后端**
（5.x 才是 GTK4 重写）。仓内已有 gtksourceview3 3.24.11（更旧的 GTK3 线），
本归档是 4.x 线，归档名 gtksourceview4（g/ 桶），与旧线异版本共存。
它是 gedit/gnome-builder 一类 GTK3 应用的**依赖项**，本次按「依赖项」独立适配。

## 上游测试（N 口径 + 逐项定性）

| 口径 | 数量 | 说明 |
|------|------|------|
| 源码包内 `tests/` 文件数（N 口径） | 105 | `find tests -type f`，含 syntax-highlighting 数据文件 |
| `testsuite/meson.build` 注册的 g_test 目标 | 23 | `test()` 注册，`meson test -C builddir --list` 可列 |
| `tests/meson.build` 手动工具程序 | 7 | 只 `executable()` 不注册 g_test（不计入 N 的上游注册数） |

**可跑性定性（依据上游源码实测的初始化调用，非推断）**：

| 类别 | 数量 | 明细 |
|------|------|------|
| 可 headless 运行 | 2 | test-buffer-input-stream（`g_test_init()`）、test-buffer-output-stream（`g_test_init()`） |
| 显示限制 | 21 | 其余全部，均调用 `gtk_test_init()` |

21 项不可跑的根因：全部经 `gtk_test_init()` 初始化，运行时 abort 于
`Gtk-WARNING **: Failed to open display`。HarmonyOS PC 无窗口系统
（无 X11/Wayland/EGL），且全系统不可 bind unix socket（HMDFS/tmpfs 权限、
`/dev/shm` 拒绝）→ Broadway 无头显示后端也无法启动，属平台限制。

消费者兜底：test_package/test_gtksourceview4.c 共 **16 项 TAP 断言**，全部走
非显示 API 路径——安装版本宏、语言管理器对包内 170 个 `*.lang` 规格做 libxml2
解析并取 `c` 语言元数据、配色管理器（7 个已安装 scheme）、Buffer 文本往返、
SearchContext 命中计数与 replace_all、undo/redo。逐项结果由 CI 日志打印。

## 编译步骤

```bash
# 源码（download.gnome.org 官方发布站）
curl -fL -o gtksourceview-4.8.4.tar.xz \
  https://download.gnome.org/sources/gtksourceview/4.8/gtksourceview-4.8.4.tar.xz
sha256sum  # 7ec9d18fb283d1f84a3a3eff3b7a72b09a10c9c006597b3fbabbb5958420a87d

export PATH=~/.local/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH
conan create archives/g/gtksourceview4/4.8.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 风险点（同族配方实测根因） | 根因 | 本配方对策 |
|---|---------------------------|------|-----------|
| 1 | `dependency('gobject-introspection-1.0')` / `vapigen` 找不到 | 4.8.4 的 meson_options 默认 `gir=true`、`vapi=true`，OHOS 无 g-ir-scanner/vapigen 交叉工具链 | generate() 显式 `-Dgir=false -Dvapi=false -Dgtk_doc=false -Dglade_catalog=false` |
| 2 | `Could not detect Ninja v1.8.2 or newer` | OHOS musl python 下 meson 对 PATH 裸名探测失败；hnp ninja ELF 需 libc++_shared.so | generate()/build() 注入 `NINJA`（绝对路径）+ 把 `/system/lib64`、SDK llvm/lib 追加进 `conanbuildenv-*.sh`（os.environ 改动会被 conan 环境重建丢弃） |
| 3 | `glib-compile-resources: Operation not permitted`（[code=126]） | glib 包 `bin/` 内宿主工具 ELF 无 `.codesign` 段，OHOS 拒绝 exec（E077）；4.8.4 的 `gnome.compile_resources()`/`mkenums_simple()` 全走这些工具 | build() 前置 `_sign_glib_tools()`：就地去 `.codesign` + `binary-sign-tool -selfSign 1` + chmod（vte 0.74.2 先例） |
| 4 | `Could not get pkg-config variable and no default provided`（glib_mkenums / glib_compile_resources） | PkgConfigDeps 生成的 `glib-2.0.pc`/`gio-2.0.pc` 不含工具变量 | generate() 注入**绝对路径**工具变量（不依赖 `.pc` 的 `${bindir}`，兼容 glib/glib2 双包名图）；同时写入 meson native `[binaries]` |
| 5 | `#include <fribidi.h>` 找不到 | fribidi.pc 只给 `-I${includedir}`，公共头在 `include/fribidi/` | `_fix_glib_pcs()` 追加 `Cflags: -I${includedir}/fribidi`（R9） |
| 6 | `.so` dlopen `Permission denied` | meson install 改写 rpath → 链接期自签名失效 | package() 先重签、再用 builddir 原始产物覆盖已安装 `libgtksourceview-4.so*`（libsoup3/gtksourceview5 先例） |
| 7 | 21 项上游测试 `Failed to open display` | 平台限制（无窗口系统、socket bind 被 SELinux 拒） | 如实申报 + 消费者 16 断言兜底；配方按 `UPSTREAM-TEST-SKIP-DISPLAY` 逐项打印，绝不计为失败 |
| 8 | CI #63489 链接 `libgtksourceview-4.so.0.0.0` 失败：`ld.lld: error: undefined symbol: g_libintl_bindtextdomain` / `g_libintl_bind_textdomain_codeset` / `g_libintl_dgettext`（引用者 `gtksourceinit.c`、`gtksourceutils.c`） | glib 的 OHOS 制品走 proxy-libintl：`glib/include/libintl.h:49` 把 `dgettext`/`bindtextdomain` 重映射到 `g_libintl_*`，实现只存在于 `glib/lib/libintl.so`（`libglib-2.0.so` 自身只是**导入**这 7 个符号）。PkgConfigDeps 按 cpp_info 重生成 `.pc`，丢掉了包内 `glib-2.0.pc` 自带的 `-lintl`；而 4.8.4 上游已移除 NLS 开关（NEWS: “remove ENABLE_NLS option, always support gettext translation”），源码无条件调用 `bindtextdomain()`/`dgettext()`，`-Wl,--no-undefined` 于是硬报错 | `_augment_pcs_intl()`：给生成的 12 个 `.pc`（`glib-2.0.pc`/`gtk+-3.0.pc`/`cairo.pc`…）的 `Libs:` 追加 `-lintl`（gtkspell3 3.0.10-r3、gtk 3.24.43 同款做法）。隔离验证：`clang -shared -Wl,--no-undefined` 只链 `-lglib-2.0` 精确复现上述 3 个未定义符号；补 `-lintl` 后链接通过，产物 `DT_NEEDED` 含 `libintl.so.8` |

## 源码修改

无。零补丁交叉编译：4.8.4 不含 `gnome.post_install()`（无 gtk-update-icon-cache
宿主工具硬依赖），meson 构建也不走 config.guess。

## 数据/资源安装布局

- `libgtksourceview-4.so.0.0.0`（soname `libgtksourceview-4.so.0`，`lib_version='0.0.0'`）
- `include/gtksourceview-4/`（公共头）
- `share/gtksourceview-4/language-specs/`（170 个 `*.lang`）、`share/gtksourceview-4/styles/`（7 个已安装 scheme，上游排除 testdark.xml）
- 消费者需自行设置 `gtk_source_language_manager_set_search_path()` 或 `XDG_DATA_DIRS`
  （OHOS 无 `/usr/share`），test_package 两种方式都做了。
