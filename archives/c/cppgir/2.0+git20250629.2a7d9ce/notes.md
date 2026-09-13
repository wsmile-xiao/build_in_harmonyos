# cppgir 2.0+git20250629.2a7d9ce 适配笔记

## 概述
- KDE GObject-Introspection C++ 绑定生成器，Debian 快照版（commit 2a7d9ce）
- 上游：https://invent.kde.org/libraries/cppgir（上游 conanfile.py 指向 gitlab mnauw/cppgir 同一项目）
- CMake 构建（也支持 meson），本适配走 CMake

## 关键适配点（实测）

### 1. expected-lite 子模块缺失
Debian orig tarball 剥离了 expected-lite git submodule（目录为空），
CMakeLists INTERNAL_EXPECTED=ON 时 file(READ expected-lite/include/nonstd/expected.hpp)
FATAL_ERROR。修复：配方 source() 阶段从 expected-lite/0.10.0 conan 包拷贝
nonstd/expected.hpp 到 expected-lite/include/。

### 2. fmt include 路径不进编译命令
上游 CMakeLists 的 pkg_check_modules(FORMAT fmt) 命中后只取 FORMAT_LIBRARIES
（LDFLAGS），FORMAT_INCLUDE_DIRS 仅在 fallback 分支 find_path；编译命令无
-I fmt/include 导致 fmt/format.h not found。且 conan fmt 包的 fmt.pc prefix
指向构建机路径（CI 产物），本地复用必须重写。修复：配方 generate() 阶段把
fmt/boost 的 includedirs 注入 CXXFLAGS 环境脚本。

### 3. 上游测试与 glib>=2.80 GValue 严格类型校验不兼容（patch 0001）
- to_int 信号 C++ 签名用 gboolean（=int）参数，gtype 推导 G_TYPE_INT，
  而 C 侧注册 G_TYPE_BOOLEAN，glib 2.88 gsignal.c:3195 CRITICAL + 断言失败
- to_string 信号用 gint64；LP64 平台 glibconfig.h 中 typedef signed long gint64
  而 cppgir 只特化了 long long，产生 G_TYPE_LONG 与注册的 G_TYPE_INT64 不匹配
修复：测试源码中 gboolean 改 bool、gint64 改 long long（5 处），仅改 test/main.cpp。
上游在更新的快照（20260518）里应已跟进 glib 严格校验。

### 4. 测试依赖
gi-test/gi-test-17 需要 gobject-2.0（glib2 包提供）。glib2 的 .pc 文件
Requires 链需要 proxy-libintl（glib2 内嵌 libintl.a）。

## 测试结论
- 上游 ctest：gi-test + gi-test-17 = 2/2 PASSED（打补丁后）
- GIR 解析生成：最小 Test-1.0.gir 生成完整 test/ 目录 14 个文件，
  _functions.hpp 含 GI_INLINE_DECL gint add(gint a, gint b) 绑定

## 产物
- bin/cppgir（生成器可执行）
- include/cppgir/gi + include/cppgir/override + include/cppgir/gi/nonstd（INTERFACE 头库）
- lib/cmake/cppgir/（CppGir::gi 导出）、lib/pkgconfig/cppgir.pc
- share/cppgir/*.ignore（默认 ignore 文件）
