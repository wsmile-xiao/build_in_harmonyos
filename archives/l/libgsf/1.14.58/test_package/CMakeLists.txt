cmake_minimum_required(VERSION 3.15)
project(test_libgsf C)

# libgsf/glib/libxml are found via pkg-config (PkgConfigDeps generator)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GSF REQUIRED IMPORTED_TARGET libgsf-1)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)
# libgsf 头文件 gsf-libxml.h 依赖 <libxml/parser.h>,需显式查 libxml-2.0
pkg_check_modules(LIBXML REQUIRED IMPORTED_TARGET libxml-2.0)
# test.c 用 g_object_unref 释放 GsfInfile,符号在 gobject-2.0 中
pkg_check_modules(GOBJECT REQUIRED IMPORTED_TARGET gobject-2.0)

add_executable(test_libgsf test.c)
target_link_libraries(test_libgsf PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)

# 上游自包含 C 测试程序 (R58: 从主配方 build() 移入 test_package)。
# 源码原样复制自 libgsf-1.14.58/tests/ check_PROGRAMS 子集, 仅使用公共 API
# (见 MANIFEST.yml 审计)。R57 预检已缓存主二进制, R58 仅改 test_package 时
# 真机 --build=missing 跳过 build(), 上游标记原先只在 build() 输出 → 从未出现;
# test_package test() 每次必跑, 故上游测试改在这里编译 + 执行 + 输出标记。
add_executable(test-ole test-ole.c)
target_link_libraries(test-ole PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)
add_executable(test-compress test-compress.c)
target_link_libraries(test-compress PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)
add_executable(test-csv test-csv.c)
target_link_libraries(test-csv PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)
add_executable(test-xml test-xml.c)
target_link_libraries(test-xml PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)
add_executable(test-msole-dup test-msole-dup.c)
target_link_libraries(test-msole-dup PRIVATE PkgConfig::GSF PkgConfig::GLIB PkgConfig::LIBXML PkgConfig::GOBJECT)
