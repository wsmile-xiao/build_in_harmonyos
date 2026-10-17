# ayatana-indicator-notifications 23.10.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (15.0.4)
- 目标: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built (conan-verify 通过，可标记 published)

## 编译步骤

1. `init-build` 下载上游 tag 归档（codeload，官方源），解压 .orig/.work
2. `conan-init` 生成配方骨架（自动模板为 autotools，重写为 CMake 配方）
3. 编写 conanfile.py + conandata.yml + test_package/（参考 ayatana-indicator-power 26.6.0 适配模式）
4. 生成 3 个补丁（SKIP_PO / XDG_AUTOSTART_DIR / main.c CLI）
5. `conan-verify` → conan create 干净构建 + 8 道门禁全部 PASS
6. test_package smoke test：`--version` 输出含 23.10.1，`--help` 正常

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 pkg_check_modules 报找不到 glib/gio/gio-unix/libayatana-common | conan 依赖不在系统 pkg-config 路径，PkgConfigDeps 生成在 generators_folder | 配方 generate() 用 PkgConfigDeps 生成 .pc，注入 -lintl 并合成 gio-unix-2.0.pc |
| 2 | gio-unix-2.0.pc 缺失 | glib 配方只导出 glib-2.0/gio-2.0/gobject-2.0 等 | 从 glib 包目录合成 gio-unix-2.0.pc（同 gtk+ 配方模式） |
| 3 | glib-2.0.pc 未列 -lintl | glib proxy-libintl 提供 g_libintl_* 符号 | _augment_glib_pkg_config 追加 -lintl |
| 4 | po/ 需要 intltool | OHOS 无 intltool 可执行 | 0001 补丁新增 SKIP_PO 选项，构建时 SKIP_PO=ON |
| 5 | XDG_AUTOSTART_DIR=/etc/xdg/autostart 绝对路径 | 会写出 package 目录之外 | 0002 补丁改为 ${CMAKE_INSTALL_PREFIX}/etc/xdg/autostart |
| 6 | D-Bus session service 无法在无 session bus 环境验证 | OHOS PC 无 session bus，程序进入 g_main_loop 阻塞 | 0003 补丁 main.c 新增 --version/--help，test_package smoke test |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：SKIP_PO 选项 + PACKAGE_VERSION 宏
- `patches/0002-data-CMakeLists.txt.patch`：XDG_AUTOSTART_DIR prefix 相对化
- `patches/0003-src-main.c.patch`：--version/--help CLI

## 依赖版本

- glib/2.84.0.1
- ayatana-common/0.9.11（pkg-config 名 libayatana-common）
- cmake-extras/1.9（GSettings CMake 模块）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify ayatana-indicator-notifications 23.10.1
# ✅ 配方验证通过，8 道门禁 (G0-G4 + L2/L4/L5) 全部 PASS
# conan create: 服务二进制 ayatana-indicator-notifications-service 构建成功
# test_package: --version → "ayatana-indicator-notifications 23.10.1" ✅
#               --help → 正常 ✅
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（含 glib -lintl / gio-unix-2.0.pc 合成 / SKIP_PO / GSETTINGS_LOCALINSTALL） |
| conandata.yml | 官方源 + sha256 + 3 补丁声明 |
| patches/ | 3 个适配补丁 |
| test_package/ | conanfile.py + test.sh + MANIFEST.yml |
---

**编译结束**: 2026-09-06 10:19
**最终状态**: built
