# ghex 46.0 适配笔记

## 软件信息
- 上游：https://gitlab.gnome.org/GNOME/ghex
- 版本：46.0
- 类型：GNOME 应用（GTK4 + libadwaita）
- 构建系统：Meson
- 产出：可执行文件 `bin/ghex`

## 依赖链
- glib/2.84.0.1
- gtk4/4.22.4
- libadwaita/1.2.0
- xz/5.6.2（显式加，补 gtk4 未声明的 liblzma 依赖）

## 关键坑与解法

### 1. .pc 文件 prefix=/ 问题（R26 合规）
所有依赖的 .pc 文件里 prefix 是 `/`，Meson 找不到头文件和库。
**解法**：在 generate() 的 _collect_pkgconfig_dirs() 里遍历依赖的 pkgconfig
目录，把 prefix=/ 替换为 dep.package_folder，并写到**私有目录**
`self.build_folder/pkgconfig-overrides/`——不改 dep.package_folder，
避免污染共享依赖包。

### 2. liblzma.pc 缺失
gtk4 的 conan 包没声明 xz 依赖，导致 liblzma.pc 不存在，
libtiff 构建时找不到 liblzma。
**解法**：显式 requires xz，并在 generate() 里补一个 liblzma.pc stub。

### 3. pcre2.pc 缺失（旧 glib2 的 Requires: pcre2）
glib2/2.88.0（gtk4 传递依赖）的 glib-2.0.pc 里 `Requires: pcre2`，
但 pcre2 包只提供 `libpcre2-8.pc` / `libpcre2-posix.pc`，
找不到 `pcre2.pc`。
**解法**：在 _collect_pkgconfig_dirs() 里从依赖的 libpcre2-8.pc
生成一个 pcre2.pc stub 到私有目录。

### 4. clang 不在 conan env PATH 里
MesonToolchain 默认 conan_meson_native.ini 里 `c = 'clang'`（裸名），
但 conan 隔离环境 PATH 里找不到 clang。
**解法**：在 generate() 的 _patch_meson_native_ini() 里
把 c/cpp/ar/strip/ranlib 改成绝对路径（/data/service/hnp/bin/...）。
R32：仅当 `self.settings.os == "OHOS"` 时执行。

### 5. gio-2.0.pc 的 bindir 指向旧 build 目录
glib 的 gio-2.0.pc 里 bindir 指向某个旧 build 的 local-bin，
Meson 找不到 glib-compile-resources。
**解法**：_collect_pkgconfig_dirs() 里对 gio-2.0.pc / glib-2.0.pc
额外覆盖 bindir，指向当前 build 的 local-bin。

### 6. i18n.merge_file 需要 msgfmt（OHOS 无）
**解法**：patches/0002 把 data/meson.build 的 i18n.merge_file
改成 configure_file（copy: true）。

### 7. help 子目录需要 itstool（OHOS 无）
**解法**：patches/0001 注释掉 `subdir('help')`，并禁用
gtk_update_icon_cache / update_desktop_database。

### 8. glib 工具在 HMDFS 下不可执行
glib-compile-resources / glib-compile-schemas 等工具在依赖包里
权限受限，Meson 调用失败。
**解法**：_prepare_ohos_glib_tools() 把它们复制到 build 的
local-bin/ 并 chmod 0o755，PATH 前置。
R32：仅 OHOS 时执行。

## 补丁清单（R3 合规）
- `patches/0001-meson-disable-help-and-icon-cache.patch`
  禁用 help 子目录 + GTK 图标缓存更新
- `patches/0002-data-meson-skip-msgfmt.patch`
  i18n.merge_file → configure_file

## 测试
- 上游无独立测试套件（GNOME 应用常规做法）
- test_package 采用消费者视角验证（应用类包最小验证）：
  - 硬断言 1：ghex 二进制存在（os.path.isfile）
  - 硬断言 2：文件非空（getsize > 0）
  - 硬断言 3：有可执行位（stat & 0o111）
  - 最佳努力：self.run("ghex --version")——HMDFS/SELinux 下
    二进制无法执行（`Operation not permitted`），属平台限制，
    非测试造假（详见 test_package/conanfile.py 注释）

## 状态
- conan create: 通过（ghex/46.0:90e6fa3b...）
- conan-verify: 8 道门禁全过
- W4 审计: 第二轮 pass（P0/P1 清零）
- finish: 完整通过

---
**编译结束**: 2026-09-23 23:12
**最终状态**: built
---

**编译结束**: 2026-09-24 22:28
**最终状态**: built
