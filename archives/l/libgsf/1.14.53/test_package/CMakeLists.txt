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
