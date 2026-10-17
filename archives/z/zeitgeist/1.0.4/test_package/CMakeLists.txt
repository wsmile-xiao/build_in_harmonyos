cmake_minimum_required(VERSION 3.15)
project(test_zeitgeist C)

find_package(zeitgeist REQUIRED)

add_executable(test_zeitgeist test_zeitgeist.c)
# test 直接 include <glib.h>（且 zeitgeist-datamodel.h 引用 glib 类型），
# 需显式 link glib 以拿到其 include 路径（zeitgeist::zeitgeist 的
# INTERFACE_INCLUDE_DIRECTORIES 不含 glib 头目录）。
# OHOS 上 glib 的 .so 引用 g_libintl_* 符号（由 glib 包内 libintl 代理
# 提供），CMakeDeps 的 glib::glib 不含它——显式链上 GLIB_LIBINTL。
target_link_libraries(test_zeitgeist PRIVATE zeitgeist::zeitgeist glib::glib)
if(DEFINED GLIB_LIBINTL AND NOT "${GLIB_LIBINTL}" STREQUAL "")
  target_link_libraries(test_zeitgeist PRIVATE "${GLIB_LIBINTL}")
endif()
