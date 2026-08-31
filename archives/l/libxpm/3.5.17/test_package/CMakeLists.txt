cmake_minimum_required(VERSION 3.20)
project(libxpm_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libxpm CONFIG REQUIRED)
find_package(GLib CONFIG REQUIRED)

add_executable(libxpm_api_surface api_surface.c)
target_link_libraries(libxpm_api_surface PRIVATE libxpm::libxpm)
target_compile_options(libxpm_api_surface PRIVATE -Werror)

add_executable(libxpm_version_contract version_contract.c)
target_link_libraries(libxpm_version_contract PRIVATE libxpm::libxpm)
target_compile_options(libxpm_version_contract PRIVATE -Werror)

# 上游 glib 驱动的测试（XpmCreate/XpmMisc/XpmRead/XpmWrite），源码未修改，
# 直接 vendored 于 upstream/test/。运行时经 G_TEST_SRCDIR 定位 pixmaps/ 数据。
# config.h 提供 configure 生成等价宏（HAVE_G_PATTERN_SPEC_MATCH_STRING /
# NO_ZPIPE）。rgb 测试需 configure 生成的内部头（xpm.h/unixio.h/file.h），
# release tarball 不含，判 N/A（详见 PR 说明）。
set(XPM_UPSTREAM_TEST_DIR ${CMAKE_CURRENT_SOURCE_DIR}/upstream/test)

foreach(t XpmCreate XpmMisc XpmRead XpmWrite)
  add_executable(${t} ${XPM_UPSTREAM_TEST_DIR}/${t}.c)
  target_include_directories(${t} PRIVATE ${XPM_UPSTREAM_TEST_DIR})
  target_link_libraries(${t} PRIVATE libxpm::libxpm glib::glib)
endforeach()
