# libayatana-indicator 0.9.5 适配笔记

## 编译环境
- 构建系统: cmake (upstream CMakeLists.txt, cmake_minimum_required 3.13)
- 编译日期: 2026-09-17
- 编译器: clang/clang++ (OHOS NDK 15.0.4, aarch64-linux-ohos)
- 状态: built

## 上游概况

- 官方源码: https://github.com/AyatanaIndicators/libayatana-indicator
- License: GPL-3.0-only（COPYING 为 GPLv3 正文；测试源文件头声明
  "GNU General Public License version 3.0"）
- 0.9.5 发布物: tarball sha256
  `73d71c908b803f12e4a5ecd8392511b58afbdd0c82ad7909611a17bb7847c5c8`

## 构建与依赖

上游根 CMakeLists.txt 以 pkg_check_modules 解析依赖：

```
DEPS = glib-2.0>=2.37, gmodule-2.0, gio-unix-2.0,
       gtk+-3.0>=3.24 (FLAVOUR_GTK3),
       libayatana-ido3-0.4>=0.8.2 (ENABLE_IDO)
```

Conan 依赖图对齐 ohpcd 已发布版本（R36 同图约束）：
glib/2.84.0.1 + gtk/3.24.43 + ayatana-ido/0.10.4（后两者均 pin glib/2.84.0.1）。

## 真实安装产物（0.9.5, FLAVOUR_GTK3+ENABLE_IDO）

| 类型 | 产物 |
|------|------|
| library | `lib/libayatana-indicator3.so.7.0.0`（SONAME `libayatana-indicator3.so.7`，VERSION 7.0.0/SOVERSION 7，ld 按规范自动生成 .so/.so.7 链接） |
| headers | `include/libayatana-indicator3-0.4/libayatana-indicator/`（indicator.h, indicator-object.h, indicator-desktop-shortcuts.h, indicator-image-helper.h, indicator-service.h, indicator-service-manager.h, indicator-ng.h） |
| pkg-config | `lib/pkgconfig/ayatana-indicator3-0.4.pc`（Requires: gtk+-3.0 libayatana-ido3-0.4） |
| tools | `libexec/libayatana-indicator/ayatana-indicator-loader3`（ENABLE_LOADER=ON 时）+ `share/libayatana-indicator/80indicator-debugging` |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接缺传递依赖库 | 上游只链接 `${PROJECT_DEPS_LIBRARIES}` 未用 `_LIBRARY_DIRS`，pkg_check_modules 的 -L 全丢 | generate() 遍历 dependencies 注入全部 libdir 到 CMAKE_SHARED/EXE_LINKER_FLAGS（同 ayatana-ido E429） |
| 2 | glib-mkenums/glib-genmarshal 找不到 | CI runner /data/service/hnp/bin 下断链符号链接污染 find_program 缓存 | tc.variables["GLIB_MKENUMS"/"GLIB_GENMARSHAL"] 显式指向 glib 包内真实脚本（同 E543） |
| 3 | 上游 tests 不可离线执行 | 依赖 dbus-test-runner（/usr/share/dbus-test-runner/session.conf）+ Xvfb（run-xvfb.sh 需要 X11 display）+ gtester 桌面 session | ENABLE_TESTS=OFF；离线验证改由 test_package 承担（纯逻辑 API） |
| 4 | glib-2.0.pc 缺 -lintl | glib 包 .pc Libs 无 intl 符号，链接报 g_libintl_ngettext undefined | test_package generate() 给 .pc 追加 -lintl（同 gtk/ayatana-ido 先例） |
| 5 | gtk_init 需要显示服务 | CI 无 X11/Wayland | 启动 gtk 包自带 broadwayd + GDK_BACKEND=broadway（同 ayatana-ido E463/E471/E527） |
| 6 | 产物无 DT_SONAME、无版本化文件名 | 上游 VERSION/SOVERSION 属性在 HarmonyOS 平台下未生成 -Wl,-soname（HMDFS 无符号链接） | 注入 CMAKE_SHARED_LINKER_FLAGS `-Wl,-soname,libayatana-indicator3.so.7`（W4/L5 门禁，同 ayatana-ido）；package() 复制 .so.7 副本保证 SONAME 可寻址 |
| 7 | static 形态不可用 | 上游 `add_library(SHARED)` 硬编码 + 核心API `indicator_object_new_from_file()` 运行时 `g_module_open()` dlopen 指示器插件 | validate() 拒绝 shared=False（ConanInvalidConfiguration），实测确认拒绝路径生效 |

## 上游测试与离线可执行性

上游 `tests/CMakeLists.txt`（ENABLE_TESTS=ON）注册 **10 个正式 ctest**：

| # | ctest 名 | 环境依赖 | 离线可执行 |
|---|----------|----------|-----------|
| 1 | service-manager-connect-tester | dbus-test-runner + session.conf | ✗（无 dbus-daemon/dbus-test-runner） |
| 2 | service-manager-no-connect-tester | dbus-test-runner + /usr/share/dbus-test-runner/session.conf | ✗ |
| 3 | service-manager-connect-nostart-tester | dbus-test-runner | ✗ |
| 4 | service-shutdown-timeout-tester | dbus-test-runner | ✗ |
| 5 | service-version-tester | dbus-test-runner + session.conf | ✗ |
| 6 | service-version-multiwatch-tester | dbus-test-runner（8 task 并发） | ✗ |
| 7 | test-desktop-shortcuts-tester | gtester + Xvfb（run-xvfb.sh） | ✗（无 Xvfb） |
| 8 | test-css-provider-leak-tester | gtester + Xvfb | ✗ |
| 9 | test-indicator-ng-tester | dbus-test-runner + gtester + Xvfb | ✗ |
| 10 | loader-tester | gtester + Xvfb | ✗ |

结论：runner 上无 dbus-daemon、dbus-test-runner、Xvfb（`which` 均空，仅
gtester 可用），全部 10 个上游测试属**环境依赖测试**，离线 CI 不可执行，
按规范不伪造通过。离线验证由 test_package 承担：GObject 类型注册 /
对象生命周期 / IndicatorDesktopShortcuts 纯逻辑分支 / 头文件可达性，
均不依赖 D-Bus session 或 X11 display（除 gtk_init 走 broadwayd 无头后端）。

## test_package 验证

- `test.c`：4 个 g_test 用例（object-type-registered / object-unref-balance /
  desktop-shortcuts-pure / service-manager-headers）+ indicator-ng.h 编译
  期验证（WITH_IDO）
- desktop-shortcuts 用真实 .desktop fixture（同上游 test-well-formed.desktop
  手法）：解析 Actions 段、nicks 枚举计数、nick→Name 映射、弱指针析构
- 走 PkgConfigDeps 链路消费 ayatana-indicator3-0.4.pc
- test() 显式 `self.run(bin_path, env="conanrun")`
- HarmonyOS 专项：llvm-readelf 检查 ELF64+AArch64、NEEDED 段
  （shared 形态含 libayatana-indicator3.so.7）、RPATH/RUNPATH 无构建目录泄漏

### 实测结果（2026-09-17, ohos-aarch64, clang-15）

shared=True（唯一支持形态）`conan create` 全流程通过：

```
100% tests passed, 0 tests failed out of 1
ok 1 /libayatana-indicator/object-type-registered
ok 2 /libayatana-indicator/object-unref-balance
ok 3 /libayatana-indicator/desktop-shortcuts-pure
ok 4 /libayatana-indicator/service-manager-headers
OHOS check: ELF64 AArch64 ✓
OHOS check: NEEDED contains libayatana-indicator3.so.7 ✓
OHOS check: RPATH/RUNPATH clean ✓
```

static=False：validate() 拒绝（ConanInvalidConfiguration，上游仅 SHARED）。

## 安装产物实测（ohos-aarch64 包）

```
lib/libayatana-indicator3.so          (SONAME libayatana-indicator3.so.7)
lib/libayatana-indicator3.so.7        (副本，保证 SONAME 寻址)
lib/pkgconfig/ayatana-indicator3-0.4.pc
include/libayatana-indicator3-0.4/libayatana-indicator/*.h (7 个公共头)
bin/libayatana-indicator/ayatana-indicator-loader3
share/libayatana-indicator/80indicator-debugging
```

## 源码修改

无源码补丁（patches/ 为空）；全部适配在 conanfile.py
generate()/package() 与 test_package 内完成。
