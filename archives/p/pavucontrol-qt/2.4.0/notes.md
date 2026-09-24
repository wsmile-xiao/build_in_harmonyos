# pavucontrol-qt 2.4.0 编译笔记

## 基本信息
- 软件: pavucontrol-qt
- 版本: 2.4.0
- 上游: https://github.com/lxqt/pavucontrol-qt
- 状态: built

## 依赖
- qtbase/6.11.1 — Qt6 Core + Widgets
- qttools/6.11.1 — Qt6 LinguistTools (lupdate, lrelease)
- lxqt2-build-tools/2.4.0 — LXQt CMake modules (LXQtTranslate, FindGLIB)
- glib/2.88.0 — GLib (found via FindGLIB.cmake from lxqt2-build-tools)
- pulseaudio/17.0.1 — PulseAudio client + libpulse-mainloop-glib

## 关键点
- pavucontrol-qt uses pa_glib_mainloop_new() from libpulse-mainloop-glib
- pulseaudio 17.0 had glib=disabled, missing libpulse-mainloop-glib
- pulseaudio 17.0.1 (PR #6643) enables glib to provide this library
- CMakeLists.txt uses CMAKE_PREFIX_PATH for lxqt2-build-tools config
- FindGLIB.cmake (from lxqt2-build-tools) uses pkg_check_modules for glib-2.0
- PkgConfigDeps generates .pc files for glib and pulseaudio

## CI 链接失败修复（2026-09-20，第 3 次尝试）
- 现象：CI（build #52858）链接 pavucontrol-qt 时全部 g_libintl_* 符号未定义；
  同一配方本地与 09-17 CI（#49345）均通过。
- 根因（已本地复现）：libglib-2.0.a 引用的 g_libintl_* 由 glib 包内置的
  proxy-libintl（libintl.a）提供，经 wrapper pc 的 Requires: glib-2.0 →
  -lintl 进入链接行。CI worker 环境残留的 LDFLAGS=-L<gettext 前缀>
  （HNP 安装的 GNU gettext，其 libintl 不导出 g_libintl_*）被 CMake 写入
  CMAKE_EXE_LINKER_FLAGS 且排在 pkg-config -L 之前，-lintl 解析到错误的
  libintl → 符号未定义。本地以
  LDFLAGS=-L/data/service/hnp/gettext.org/gettext_0.26/lib 复现出完全相同的
  7 个未定义符号。
- 修复（两层防护，均在 conanfile.py generate()）：
  1. 环境清洗（R33）：清空 LDFLAGS/CPPFLAGS/LIBRARY_PATH/CPATH/
     C_INCLUDE_PATH/CPLUS_INCLUDE_PATH，杜绝 worker 环境注入；
  2. wrapper libpulse-mainloop-glib.pc 的 Libs 行加入 glib 包内
     proxy-libintl 的绝对路径，即使 -lintl 被遮蔽也能解析 g_libintl_*。
- 验证：LDFLAGS+LIBRARY_PATH+CPPFLAGS 三重指向 GNU gettext 的敌意环境下
  conan create 通过，产物二进制含已解析的 g_libintl_* 符号（nm 确认 T）。

---
**编译结束**: 2026-08-27
**最终状态**: built
**CI 链接修复**: 2026-09-20
