# gtksourceview5 5.22.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-26
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 15.0.4 工具链，aarch64-unknown-linux-ohos）
- 状态: built（本地 conan create 全绿；CI 上游同配方）
- 任务: wave12 #14254（j669539）

## 背景

GtkSourceView 5 是 GNOME 的语法高亮文本组件库（GTK4 生态，gedit/gnome-builder
等使用）。仓内已有 gtksourceview3 3.24.11（v3 旧线，GTK3），本归档是 v5 新线
（GTK4），与旧线异版本共存，归档名 gtksourceview5（g/ 目录）。

## 上游测试（rule4/N 口径 + 逐项定性）

上游 meson 注册测试目标 26 个（testsuite/meson.build 的 testsuite_sources
26 项；tests/meson.build 的 8 个是手动测试工具程序不注册 g_test，不计入 N）。

**实测结果（本机 OHOS arm64 真跑）**：

| 类别 | 数量 | 明细 |
|------|------|------|
| 可跑且全 PASS | 2 | test-buffer-input-stream（6 断言）、test-buffer-output-stream（9 断言） |
| 显示限制不可跑 | 24 | 其余全部（见下） |

24 项不可跑的根因（实测确认，非推断）：
- 24 项全部调用 `gtk_test_init()`/`gtk_init()`，运行时 abort 于
  `Gtk-WARNING **: Failed to open display`（SIGABRT/退出码 1）。
- HarmonyOS PC 无窗口系统（无 X11/Wayland/EGL）。gtk4/4.22.4 在本仓是
  Broadway-only 构建，唯一无头显示途径 broadwayd 的 unix socket bind 被
  SELinux 拒绝（`GUnixSocketAddress: Operation not permitted`，全系统
  HMDFS/tmpfs 均不可 bind unix socket，实测 /dev/shm 权限拒绝、HMDFS
  EPERM）→ Broadway 显示服务器无法启动，24 项显示依赖测试在 OHOS 上
  属平台限制。
- 消费者兜底：test_package 的 8 断言测试真实覆盖了库核心 API 路径
  （版本 API、LanguageManager 180 个语言 spec 的 libxml2 解析、
  StyleSchemeManager、GtkSourceBuffer 创建/高亮设置），ALL PASS。

display-limited 24 项清单：test-buffer、test-completion-words、test-encoding、
test-iter、test-language、test-languagemanager、test-mark、test-regex、
test-region、test-snippets、test-utils、test-stylescheme、
test-styleschememanager、test-vim-state、test-vim-text-object、
test-file-loader、test-file-saver、test-language-specs、test-printcompositor、
test-search-context、test-space-drawer、test-syntax、test-view、test-vim-input。

## 编译步骤

```bash
# 源码（download.gnome.org 官方镜像；gitlab.gnome.org 的权威发布镜像）
curl -fL -o gtksourceview-5.22.0.tar.xz \
  https://download.gnome.org/sources/gtksourceview/5.22/gtksourceview-5.22.0.tar.xz
sha256sum  # 3ebce33c781e65590a450ecd3ffade480d8e3135b52ee996f1620d6c7dffbbff

export PATH=~/.local/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH
conan create archives/g/gtksourceview5/5.22.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pcre2 版本冲突 | glib/2.84.0.1.1 pin pcre2/10.45，我方初 pin 10.48 | `self.requires("pcre2/10.45", override=True)` 对齐 |
| 2 | `Unknown option: build-tests` | gtksourceview 的选项名是 build-testsuite（build-tests 是 gtk4 的） | 只设 build-testsuite=true |
| 3 | meson `Subproject pcre2 is buildable: NO` | pcre2 配方只发 pcre2.pc，上游探测组件名 libpcre2-8 | `_forward_pc("pcre2","libpcre2-8")` |
| 4 | `Could not detect Ninja v1.8.2` | OHOS musl python 的 subprocess 对 PATH 裸名解析失败（hnp ninja 是 symlink） | generate() 注入 `os.environ["NINJA"]=绝对路径`（meson detect_ninja 首选 NINJA env） |
| 5 | test 阶段 `Error relocating cmake: _ZdlPv` | conan buildenv 重写 LD_LIBRARY_PATH 后丢失 libc++_shared.so 所需路径 | test_package build() 显式前置 SDK llvm/lib 与 /system/lib64 |
| 6 | 上游测试 rc=127 | build_folder 语义：layout folders.build=builddir → build_folder 已含 builddir | 测试二进制路径用 build_folder/testsuite（双路径探测兜底） |
| 7 | .so dlopen Permission denied 风险 | meson install 改写 .so 致 .codesign 失配 | package() 用 builddir 原始产物覆盖 + _sign_shared_libs 重签（ML-0043） |
| 8 | 24 项测试 Failed to open display | OHOS 无窗口系统；Broadway socket 被 SELinux 禁 | 如实申报平台限制 + test_package 消费者兜底（180 语言 spec 解析实测通过） |
| 9 | HMDFS 残留缓存目录无法删 | E046 平台特性 | 手动 rm -rf + chmod u+w 后重试 |
| 10 | CI `Program 'gtk-update-icon-cache' not found`（本机 meson 1.12 仅警告所以本地绿） | CI worker 的旧 meson 对 gnome.post_install 缺失 host 程序硬报错；图标缓存更新属桌面部署步骤 | patches/0001 移除 gnome.post_install(gtk_update_icon_cache: true) |
| 11 | CI `[code=126] glib-compile-resources: Operation not permitted`（第二轮，全部 gresource 自定义目标失败；本机绿因本机 glib 包缓存工具已签名） | CI worker conan 缓存的 glib 包 bin/ 内 host 工具 ELF 无 .codesign 段，OHOS XPM 拒绝 exec（E077） | build() 前置 _sign_glib_tools()：就地移除旧段+binary-sign-tool 自签+chmod（vte 0.74.2 同款先例） |

## 源码修改

- patches/0001-meson-remove-gtk-update-icon-cache-post-install.patch（portability）：
  移除 `gnome.post_install(gtk_update_icon_cache: true)`——CI worker 无
  gtk-update-icon-cache 宿主工具，老版 meson 视为 configure 硬错误
  （meson 1.12 仅 WARNING "installation without DESTDIR will fail"）。
  其余平台差异全部在配方层解决（meson 选项 + pkg-config 转发 + 签名）。

## 依赖版本

- gtk4/4.22.4（Broadway-only，ohpcd 已发布）
- glib/2.84.0.1.1（shared，override 对齐全图；glib2/2.88.0 经 gtk4 链传递存在但非直接依赖）
- libxml2/2.15.3.1
- pcre2/10.45（override 对齐 glib pin）
- fribidi/1.0.16
- zlib/1.3.1.1（override 消冲突，PIC 变体）

## 产物

- libgtksourceview-5.so（含重签）
- share/gtksourceview-5/language-specs（180 语言）、styles、snippets

## 注意事项（下游）

- 下游消费建议 `gtksourceview-5::gtksourceview-5` cmake target 或
  pkg-config gtksourceview-5
- test/下游运行需 LD_LIBRARY_PATH 含 gtksourceview5/glib/gtk4 的包 lib 目录
- meson 下游（如 gnome-text-editor）需同样注入 NINJA env（OHOS musl python 通病）
- 上游 24 显示依赖测试在无显示环境恒 SIGABRT，勿纳入下游 CI 门禁
---

**编译结束**: 2026-09-26 06:46
**最终状态**: built
