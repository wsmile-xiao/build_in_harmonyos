# roxterm 3.18.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-03
- 编译器: clang（OHOS SDK native llvm）
- 状态: published
- Profile: ohos-aarch64（本机鸿蒙PC真机 aarch64，OHOS 适配版 Conan 2.29.1）

## 编译步骤

`conan create archives/r/roxterm/3.18.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同 --build=missing --user=ohpcd --channel=stable`（经 `ohc-run.py conan-verify` 门禁执行）。

关键配方动作（conanfile.py generate()）：
1. PkgConfigDeps 生成 pc 文件，并补三个别名：`dbus-1.pc`←dbus.pc、`libpcre2-8.pc`←pcre2.pc、`gmodule-export-2.0.pc`←gmodule-2.0.pc（含 `-Wl,--export-dynamic`，roxterm-config 的 GtkBuilder 信号回调依赖）。
2. `glib-2.0.pc` Libs 追加 `-lintl`（与 gtk/vte/gspell 同修）。
3. CMakeToolchain：`Intl_ROOT`/`CMAKE_INCLUDE_PATH`/`CMAKE_LIBRARY_PATH` 指向 glib 包内 proxy-libintl；`BUILD_MANPAGES=OFF`；`CMAKE_PROGRAM_PATH` 指向 staged 工具目录；`CMAKE_POLICY_VERSION_MINIMUM=3.10`。
4. Staging：glib 包 `bin/glib-compile-resources` 复制到 build/conan-native-tools（objcopy 去 .codesign + binary-sign-tool selfSign 重签），外面包一层 shell wrapper 在 exec 前把 glib libdir 置前 LD_LIBRARY_PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | glib-compile-resources 报 libffi.so.8 找不到 | CMake 裸命令解析到 /data/service/hnp/bin 的 ambient 副本（E463），其依赖 libffi 不在默认路径 | 补丁改显式 find_program + CMAKE_PROGRAM_PATH 引导到 staged 副本（E527：conan 缓存 ELF 在 HMFS 不可执行，须复制+重签） |
| 2 | staged 工具报 g_libintl_* 符号找不到 | gettext 与 glib proxy-libintl 同 SONAME libintl.so.8 但符号集不同；聚合 conanbuildenv-release-armv8.sh 整体重写 LD_LIBRARY_PATH 且总在自定义脚本之后 source，gettext libdir 遮蔽 glib | shell wrapper 在 exec 前强制 glib libdir 置前 LD_LIBRARY_PATH（HMFS 上 patchelf 不可写，无法走 RPATH） |
| 3 | man 页生成失败 | man/CMakeLists.txt 用 xsltproc 在线拉 docbook.xsl，离线 CI 无网 | 补丁加 BUILD_MANPAGES 选项（上游默认 ON 不变），配方传 OFF |
| 4 | expat 版本冲突 | dbus-glib requires expat/2.8.2，与依赖树 2.8.2.1 冲突 | `requires("expat/2.8.2.1", override=True)` |

## 源码修改

- `patches/0001-man-CMakeLists.txt.patch`：新增 `option(BUILD_MANPAGES)`，条件改 `XSLTPROC AND BUILD_MANPAGES`。
- `patches/0002-src-CMakeLists.txt.patch`：glib-compile-resources 裸命令改 `find_program(GLIB_COMPILE_RESOURCES_EXECUTABLE)`，找不到则 FATAL_ERROR。

## 依赖版本

vte/0.74.2、gtk/3.24.43、glib/2.84.0.1、pango/1.56.4、cairo/1.18.4.2、dbus/1.14.10、dbus-glib/0.114.1、pcre2/10.45、expat/2.8.2.1（override）、gettext/0.22.5.1（tool_requires, msgfmt）。

## 验证结果

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify roxterm 3.18.2
# G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
# test_package: AArch64 动态 ELF 确认（roxterm + roxterm-config），NEEDED 闭包 32 库完整，
# headless 探针 PASS（GTK init "Cannot open display" = 库加载成功）
```

## 交付物

| 文件 | 说明 |
|------|------|
| roxterm/3.18.2@ohpcd/stable | conan 包（bin/roxterm、bin/roxterm-config） |

## 注意事项

- 上游无单元测试（无 enable_testing/add_test），MANIFEST.yml N=0 已记录。
- OHOS 工具链 --as-needed：两个二进制只用 GDBus(gio) 符号，libdbus-1/libdbus-glib-1 不在直接 NEEDED，pcre2 经 glib 传递；test_package 断言按实际直接闭包（vte/gtk/gdk/glib）。
- 升级修复版本规则 R37：本包若有后续修复须递增为 3.18.2.1。
---

**编译结束**: 2026-10-03 09:21
**最终状态**: published
