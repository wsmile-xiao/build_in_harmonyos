# adapta-gtk 3.95.0.11 适配笔记

## 基本信息
- **软件名称**：adapta-gtk（平台库名；上游项目名为 adapta-gtk-theme）
- **上游真实项目**：adapta-project/adapta-gtk-theme（"An adaptive Gtk+ theme based
  on Material Design Guidelines"）
- **版本**：3.95.0.11（上游 tag 3.95.0.11，2018-10-02 发布，上游最后一次 stable release）
- **许可证**：GPL-2.0（COPYING）+ CC-BY-SA-4.0（LICENSE_CC_BY_SA4）
- **上游仓库**：https://github.com/adapta-project/adapta-gtk-theme
- **类型**：GTK2/GTK3 主题数据包（autotools 构建，SCSS 源由 sassc 编译为 CSS，
  SVG 源由 inkscape 渲染为 PNG 资产）

## 三重身份映射（名称差异必须说明）
- 平台身份：adapta-gtk / 3.95.0.11 / Issue #2026 / 分支 feat/adapta-gtk-3.95.0.11
- 上游身份：adapta-project/adapta-gtk-theme / tag 3.95.0.11 / GitHub / GPL-2.0 + CC-BY-SA-4.0
- 归档身份：Conan adapta-gtk/3.95.0.11 / archives/a/adapta-gtk/3.95.0.11

**名称差异解释**：任务平台库名 "adapta-gtk" 与上游仓库名 "adapta-gtk-theme" 不同。
上游项目的安装产物即主题目录名 Adapta / Adapta-Nokto / Adapta-Eta /
Adapta-Nokto-Eta（无 "-theme" 后缀），Arch Linux 官方包名亦为
adapta-gtk-theme（3.95.0.11-4，Upstream URL 指向 adapta-project/adapta-gtk-theme）。
两者指向同一上游项目的同一 tag 3.95.0.11，版本号一致，无版本歧义。
归档 Conan 包名按任务平台库名取 adapta-gtk；主题目录内标识符保持上游原名
（GTK 通过 index.theme 的 GtkTheme= 字段解析主题目录名，保持原名才能被桌面正确加载）。

## 源码与校验
- **上游源码 tarball（官方 release）**：
  - URL: https://github.com/adapta-project/adapta-gtk-theme/archive/refs/tags/3.95.0.11.tar.gz
  - SHA256: fb8fc11b770be59e1673b8f2d917704fc34e53aee5fb02fed70d83909d3309bd
  - 已实际下载并核验（codeload 官方端点，gzip 数据，664,080 字节；与 Solus 官方
    记录一致）。解压 456 个文件，为 autotools 源码包（configure.ac + Makefile.am +
    gtk/sass/SCSS 源 + gtk/asset/SVG 源），**不含**任何预编译 CSS/gresource
    （0 个 .css/.gresource）。
- **编译主题数据源（FreeBSD 官方二进制包）**：
  - URL: https://pkg.freebsd.org/FreeBSD:13:amd64/quarterly/All/adapta-gtk-theme-3.95.0.11_5.pkg
  - SHA256: 981533ccb69f53f1fec8f378fbc16b613ae4605192c6703e7c4016e7cde5bac2
  - 已实际下载并核验（xz 压缩 tar，681,852 字节）。+MANIFEST 确认 pkgname=
    adapta-gtk-theme-3.95.0.11_5、port 上游为 adapta-project/adapta-gtk-theme
    （_5 为 FreeBSD port revision，源码仍为同一上游 tag 3.95.0.11，由
    sassc+inkscape 构建）。quarterly 与 latest 分支包内容哈希一致（已验证）。
  - 包内含 usr/local/share/themes/ 下四个完整主题变体（Adapta 380 文件、
    Adapta-Nokto 278 文件、Adapta-Eta 241 文件、Adapta-Nokto-Eta 234 文件，
    各含 gtk-2.0 rc、gtk-3.0/3.22/3.24 CSS+gresource、index.theme、
    gnome-shell/metacity/xfwm4/cinnamon/openbox 等 DE/WM 资产），
    与上游 make install 的目标结构一致；index.theme / gtk.css / gtk.gresource /
    GPLv2 / CC-BY-SA-4.0 哈希与上游编译产物逐字节一致（已对比验证）。
- **许可证**（从上游官方仓库 tag 3.95.0.11 下载并核验 SHA256）：
  - COPYING（GPL-2.0）：8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643
  - LICENSE_CC_BY_SA4（CC-BY-SA-4.0）：9348ddfd44da5a127c59141981954746a860ec8e03e0412cf3af7134af0f97e2

## 构建说明（为何是数据包 + 数据来源决策）
- 上游构建系统为 autotools（configure.ac + Makefile.am），configure 强制要求
  sassc 与 inkscape（AC_MSG_ERROR），构建期需：
  - sassc（SCSS→CSS，parse-sass.sh / Makefile.am 调用 `sassc -M -t compact`）
  - inkscape（SVG→PNG 按 id + DPI 导出 189+ gtk3 资产与 gtk2/wm 资产）
  - glib-compile-resources（gtk.gresource）、glib-2.0.pc、gdk-pixbuf-2.0.pc
- OHOS 构建环境实测：sassc/inkscape 完全不可用（制品仓无配方、cmd-pkgs 无预编译
  包、pip libsass wheel 对 OHOS clang 构建失败、imagemagick 不支持按 SVG id 导出），
  glib/gdk-pixbuf 开发包亦缺失 → 无法从源码完整构建（与 adw-gtk 6.5 的 sass 缺失
  属同类平台限制，但 adw-gtk 上游 release 自带编译产物，而 adapta-gtk-theme
  上游 release 只有源码）。
- 因此采用**数据包**方案（参照同仓库 adw-gtk 6.5、adw-gtk3 6.5、adwaita-fonts、
  adwaita-icon-theme 先例）：使用与上游同一 tag 3.95.0.11 的 FreeBSD 官方编译
  产物（由 sassc+inkscape 构建），`source()` 下载并核验 SHA256 后安装
  share/themes/{Adapta,Adapta-Nokto,Adapta-Eta,Adapta-Nokto-Eta} 与
  share/licenses/adapta-gtk/{COPYING,LICENSE_CC_BY_SA4}。
- `build()`：无需编译（数据包）；`package_info()`：主题数据包无 cpp_info。
- 无补丁、无 wrapper、无本机路径进入归档。

## 上游测试统计
- **上游自动化测试数量**：0（零）
- **依据**：
  - 上游源码 tarball（456 文件）内无 `test/` 或 `tests/` 目录（TEST_DIR_COUNT=0）
  - 顶层与 gtk/shell/wm/extra 各 Makefile.am、configure.ac 中均无
    TESTS / check_PROGRAMS / make check / check-local 定义（grep 全部无命中）
  - 上游无 CI 测试 job（GitHub release 仅有源码 tarball + .asc 签名）
  - 主题数据包无二进制 CLI 入口
- 消费者测试由 test_package/test_theme.py 补齐（见下）。

## 验证结果
- **conan-verify adapta-gtk 3.95.0.11**：见 reports/（G0-G4/L2/L4/L5）
- **test_package**：消费者断言（4 变体 index.theme 与 GtkTheme 映射、
  gtk-3.0/3.22/3.24 CSS 与 gtk.gresource 非空、gtk-2.0 rc、gnome-shell/
  metacity/xfwm4/cinnamon 资产、GPL-2.0 与 CC-BY-SA-4.0 许可证）
- **finish adapta-gtk 3.95.0.11 built**：已完成（仅 built，未 published）

## 特殊说明
- 数据包类型 `package_type = "application"`，无 `cpp_info`。
- 使用 Conan 2 `download()` 下载数据源与许可证，遵循 SHA256 校验。
- 数据源为 FreeBSD .pkg（xz 压缩 tar），`source()` 用 Python 标准库 tarfile
  以 "r:xz" 解压，零第三方原生扩展（CI #18008 二次修复：原 Arch .tar.zst 需
  zstandard 原生 .so，被 OHOS code-signature 检查拒绝：ImportError: Permission
  denied；本方案不再有该依赖，无需 pip 安装、无需签名）。
- 与 adw-gtk（Issue #2015，archives/a/adw-gtk/6.5）、adw-gtk3（Issue #2002，
  archives/a/adw-gtk3/6.5）为不同上游、不同平台库名的独立任务；本归档只使用
  archives/a/adapta-gtk/3.95.0.11。
---

**编译结束**: 2026-08-11 17:19
**最终状态**: built
