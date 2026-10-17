# gdk-pixbuf 2.44.6.1.1 适配笔记

> R37/L0j：本版本为 gdk-pixbuf 2.44.6 配方的适配修复后缀版（再次递增）。远端 ohpcd
> 制品仓已存在 gdk-pixbuf/2.44.6（2026-08-04 发布，revision dd84a01a，配方启用 libtiff/4.7.2）
> 与 gdk-pixbuf/2.44.6.1（2026-08-22 发布，revision fa6c6d19，仍启用 libtiff）。本地配方
> 修改了 conanfile.py/conandata.yml（tiff 禁用 + glib/libpng/libjpeg-turbo 依赖集），
> cnb.cool 制品仓不支持同版本多 revision 并存 → 按 R37 递增为 2.44.6.1.1。
> 源码仍为官方 2.44.6 tarball。

## 编译环境
- 构建系统: meson（registry autotools 提示错误，2.44.x 实际是 meson）
- 编译日期: 2026-08-31
- 编译器: clang 15（OHOS PC aarch64 本机构建）
- 状态: built

## 编译步骤

1. 依赖环境：`conan install`（PkgConfigDeps 生成 .pc + MesonToolchain 生成 native ini）
2. 应用补丁：3 个补丁（0001 gen-thumbnailer.py、0002 gdk-pixbuf/meson.build、0003 thumbnailer/meson.build）
3. 配置：`meson setup build --prefix=$DEFAULT_PREFIX -Dgio_sniffing=false -Dtiff=disabled -Dtests=false -Dman=false -Dintrospection=disabled`
4. 编译：`ninja -C build`（150/150 目标，仅 pixops.c -Wcast-align 警告，上游已知非阻塞）
5. 安装：`meson install -C build --destdir=$TEST_PREFIX`（staging 验证通过）
6. 测试：`meson test`（-Dtests=false 无测试）；运行时冒烟测试 PASS（ELF 签名后）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 找不到下载 URL | registry 无 URL | 用官方 GNOME 源 `--url=https://download.gnome.org/sources/gdk-pixbuf/2.44/gdk-pixbuf-2.44.6.tar.xz` |
| 2 | 2.42.12 的 0002 补丁不适用 2.44.6 | 2.44 源码行号变化 + loaders.cache command 参数改为三目表达式 | 按 2.44.6 源码重新生成 0002 补丁（逻辑不变：禁用 loaders.cache custom_target） |
| 3 | 构建产物未签名无法执行 | HarmonyOS ELF 签名要求 | 配方 package() 用 binary-sign-tool 重签（env=None，见 E255 草稿） |
| 4 | 缺 shared-mime-info/libtiff/rst2man | gio_sniffing/tiff/man 默认启用 | 禁用 gio_sniffing/tiff/man/tests 选项 |
| 5 | 构建期执行宿主二进制 | loaders.cache/thumbnailer custom_target | 补丁改为空分支/configure_file |

## 源码修改（3 个补丁，同族 2.42.12 复用 + 适配）

### 0001-build-aux-gen-thumbnailer.py.patch
- gen-thumbnailer.py 仅在提供 loaders 路径时设置 GDK_PIXBUF_MODULE_FILE

### 0002-gdk-pixbuf-meson.build.patch（按 2.44.6 重新生成）
- 修改 loaders.cache custom_target：`if not meson.is_cross_build()` → `if meson.is_cross_build() or true`，
  走空分支，避免构建期执行 gdk-pixbuf-query-loaders
- 2.44 相比 2.42 的差异：`command: [gdk_pixbuf_query_loaders, dynamic_loaders.length() > 0 ? dynamic_loaders : '']`（三目参数）

### 0003-thumbnailer-meson.build.patch
- thumbnailer custom_target → configure_file（避免执行 gdk-pixbuf-print-mime-types）

## 依赖版本（conan 配方实际使用，已发布到制品仓）

- glib: 2.84.0.1（自带 proxy-libintl，libintl.h 宏重定向 gettext→g_libintl_*）
- libpng: 1.6.58
- libjpeg-turbo: 3.2.0
- zlib: 1.3.1.1（传递依赖）
- meson: 1.11.1（环境工具）
- ninja: 1.13.1（环境工具）

## 2.44.6 相对 2.42.12 的 API/源码变化

1. `gdk-pixbuf-autocleanups.h` 从安装头文件列表移除
2. 新增 android（io-android-*.c）与 glycin（io-glycin-*.c）loader 源码（默认未启用，不影响构建）
3. 其余影响配方构建的结构（loaders.cache/thumbnailer/marshal/enums/pkgconfig）与 2.42.12 一致

## Conan 配方验证

- `conan create` G2: PASS（干净源码构建 + test_package 调用真实 gdk-pixbuf API 运行通过：`gdk-pixbuf 2.44.6 OK: 16x16 channels=4 has_alpha=1`）
- conan-verify G0-G4 + L2/L4/L5: PASS（`.conan-verified` 标记已写入）
- 产物：libgdk_pixbuf-2.0.so.0.4400.6 + gif loader + 4 个命令行工具 + 12 个头文件 + gdk-pixbuf-2.0.pc
- 关键修复（复用 2.42.12 经验）:
  1. generate() 合成 `gmodule-no-export-2.0.pc`（含 gmodule_supported=true）
  2. 向 glib pc 注入 -lintl + glib_genmarshal/glib_mkenums 变量（staged 工具）
  3. package() 中 meson.install() 后用 `binary-sign-tool` 重签 ELF（env=None）
  4. meson 选项 `introspection` 是 feature 类型，传 "disabled" 而非布尔 False

## 交付物

| 文件 | 说明 |
|------|------|
| manifest.yaml | 编译元数据（status=built） |
| notes.md | 本文件 |
| conanfile.py | Conan 配方（meson + PkgConfigDeps + glib 工具注入 + ELF 重签） |
| conandata.yml | 官方源码 URL + sha256 + 3 补丁声明 |
| patches/0001-0003 | 3 个补丁 |
| test_package/ | conanfile.py + test.c + CMakeLists.txt + MANIFEST.yml |
| reports/test-report.md | 探索构建测试报告 |
| reports/conan-verify-report.md | conan-verify 门禁报告 |

## 知识草稿（路径 B 知识库贡献）

- `knowledge/drafts/E321-draft-23CE.kv` / `.md`（draft=true，不 promote）
  - 主题：PkgConfigDeps 不生成 `gmodule-no-export-2.0.pc` 导致 meson configure 失败
  - 方案：recipe `generate()` 中手工合成 `.pc`（含 `gmodule_supported=true`、`Requires: glib-2.0`）
- `knowledge/drafts/E322-draft-2F28.kv` / `.md`（draft=true，不 promote）
  - 主题：OHOS ELF 重签必须用 `env=None`，conanbuild env 破坏 binary-sign-tool
  - 方案：`package()` 中 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签，`self.run(..., env=None)`
- 查重：knowledge/ 无 gdk-pixbuf/gmodule-no-export-2.0/OHOS 重签主题既有条目；与 E123（glib proxy-libintl）、E090（meson host_system）为不同主题

### 对话 #1 [2026-08-30]

- 问题: init-build 找不到下载 URL（registry 无 gdk-pixbuf 2.44.6 条目，autotools 提示错误）
- 操作: 用官方 GNOME 源显式指定 `--url=https://download.gnome.org/sources/gdk-pixbuf/2.44/gdk-pixbuf-2.44.6.tar.xz`；确认 2.44.x 实际使用 meson 构建
- 结果: 源码下载/解压完成，meson 构建环境就绪

### 对话 #2 [2026-08-31]

- 问题: 2.42.12 的 0002 补丁不适用于 2.44.6 源码（loaders.cache custom_target 的 command 参数改为三目表达式）
- 操作: 按 2.44.6 源码重新生成 0002 补丁，逻辑不变（禁用构建期执行 gdk-pixbuf-query-loaders）
- 结果: 3 个补丁在干净源码上全部适用

### 对话 #3 [2026-08-31]

- 问题: 配方复用 2.42.12 经验但版本被 R37 门禁拦截（远端 ohpcd 已有 gdk-pixbuf/2.44.6，配方不同）
- 操作: 按 R37 递增后缀为 2.44.6.1（源码仍为官方 2.44.6 tarball），L0j 版本占用检查通过
- 结果: conan create / conan-verify（G0-G4 + L2/L4/L5）全 PASS，W3 本地 CI 模拟全绿

### 对话 #4 [2026-09-01]

- 问题: CI L0j 再次拦截——远端 ohpcd 已存在 gdk-pixbuf/2.44.6.1（2026-08-22 发布 revision fa6c6d19，libtiff 启用版），本地配方（tiff 禁用）与之不同
- 操作: 按 R37 再次递增后缀为 2.44.6.1.1（源码仍为官方 2.44.6 tarball），更新目录、conandata.yml、conanfile.py、manifest.yaml、notes.md、test_package、顶层 manifest/commands/README
- 结果: 本地 knowledge_check.sh 通过；等待 CI 重跑验证 L0j 通过

---
**编译结束**: 2026-08-30
**最终状态**: built
---

**编译结束**: 2026-09-01
**最终状态**: built
