# ayatana-common 0.9.11 适配笔记

## 软件简介
libayatana-common（Ayatana 系统指示器的公共库）：桌面会话检测
（Lomiri/Unity/GNOME/MATE/XFCE/PANTHEON/Budgie）、程序查找、命令/URL
执行辅助、以及 org.ayatana.common GSettings schema。CMake 构建，纯 C，
产物为共享库 libayatana-common.so + 头文件 + pkg-config + gschema。

## 编译环境
- 构建系统: cmake（自动检测为 autotools，已手工修正）
- 编译器: clang 15 (aarch64-linux-ohos)
- Conan profile: ci/conan/profiles/ohos-aarch64
- 依赖: glib/2.84.0.1（含 gio-2.0/gobject-2.0 等模块 .pc）

## 编译步骤（手动探索）
```bash
# 用 conan full_deploy 提供 glib 2.84.0.1 的 .pc（修正 prefix=/ 为真实路径）
export PKG_CONFIG_PATH=$HOME/tmp/pc-fix
export LD_LIBRARY_PATH=<glib-deploy>/glib/2.84.0.1/.../lib:...
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DENABLE_TESTS=ON \
         -DCMAKE_CXX_STANDARD=17 -DCMAKE_PREFIX_PATH=<gtest-deploy> \
         -DCMAKE_MODULE_PATH=$HOME/tmp/cmake-mod
make -j2 && ctest
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(GSettings REQUIRED)` 失败 (data/) | GSettings 模块来自 Ubuntu cmake-extras，OHOS 无 | 新增 cmake/FindGSettings.cmake 提供 add_schema（0002 补丁） |
| 2 | `find_package(Intltool REQUIRED)` 失败 (po/) | Intltool 模块来自 Ubuntu cmake-extras，OHOS 无 | 顶层 CMakeLists 用 find_package(Intltool QUIET) 守卫 add_subdirectory(po)（0001 补丁） |
| 3 | 链接报 `unable to find library -l:ld-musl-aarch64.so.1` | 手动探索用 base glib/2.84.0 的 .pc 带 musl 参数，且 -L 路径被 pkg_check_modules 丢弃 | conan 用 glib/2.84.0.1（模块 .pc 绝对路径），无需手工 LDFLAGS |
| 4 | tests 缺 gtest/gtest.h | 上游测试依赖 gtest/gmock/vala | conan 构建关闭 ENABLE_TESTS；功能覆盖由 test_package 提供（调用真实 API） |
| 5 | CI 链接报 `unable to find library -lgio-2.0/-lgobject-2.0/-lgmodule-2.0/-lglib-2.0/-lintl` | 上游只链 `${DEPS_LIBRARIES}`，pkg_check_modules 丢弃 `-L`（DEPS_LIBRARY_DIRS）；本地 shell 因 `~/.zshrc` 导出 `LDFLAGS=-L$HOME/usr/local/lib` 掩盖了问题，CI 无该变量即失败 | 顶层 CMakeLists 在 `include_directories` 后加 `link_directories(${DEPS_LIBRARY_DIRS})`（0003 补丁），构建自包含，不再依赖环境 LDFLAGS |

## 源码修改
- `0001-CMakeLists.txt.patch` — po/ 翻译可选（Intltool 缺失时跳过）
- `0002-cmake-FindGSettings.cmake.patch` — 新增 FindGSettings.cmake（cmake-extras 替代，安装 gschema）
- `0003-link-glib-libdirs.patch` — 顶层 CMakeLists 增加 `link_directories(${DEPS_LIBRARY_DIRS})`，恢复 pkg_check_modules 丢失的 `-L` 搜索路径（链接 glib/gio/gobject/gmodule/intl）

## 依赖版本
- glib/2.84.0.1（ohpcd 已发布；提供 glib-2.0/gio-2.0/gobject-2.0 等模块 .pc）
- gtest/1.17.0（ohpcd 已发布，仅探索期跑上游测试用，不在配方内）

## 验证结果
- 上游测试（探索期，ENABLE_TESTS=ON + gtest/1.17.0）：
  ```
  ctest: 1/1 Test #1: TstUtils ... Passed
  [ PASSED ] 9 tests (isLomiri/isUbuntuTouch/isGnome/isUnity/isMate/isXfce/
                      isPantheon/isBudgie/ellipsize)
  ```
- DESTDIR staging：lib/pkgconfig/libayatana-common.pc、include/ayatana/common/utils.h、
  lib/libayatana-common.so、share/glib-2.0/schemas/org.ayatana.common.gschema.xml

## 交付物
- conanfile.py（CMake 配方，requirements glib/2.84.0.1）
- conandata.yml（官方 URL + sha256 + 3 补丁声明；镜像 fallback 由 CI 自动添加）
- test_package/（test.c 调用 is_gnome/have_program 真实 API）
- patches/（3 个 portability 补丁）

## 注意事项
- 上游 `add_library(ayatana-common SHARED ...)` 固定构建共享库，BUILD_SHARED_LIBS
  选项对 src/ 无实际影响。
- po/ 翻译与 GObject-Introspection/Vala 绑定未构建（OHOS 无对应工具链）。
- /tmp 只读（E002）：TMPDIR=$HOME/tmp。
---

**编译结束**: 2026-09-03 09:19
**最终状态**: built
