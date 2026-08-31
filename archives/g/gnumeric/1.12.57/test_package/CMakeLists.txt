cmake_minimum_required(VERSION 3.15)
project(test_gnumeric C)

# gnumeric 是 autotools 应用+库，通过 pkg-config 发现（PkgConfigDeps 生成 .pc）。
# libspreadsheet 头文件会展开包含 goffice/gtk/cairo/pango/gsf/glib 头文件，
# 故显式声明这些模块。
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSPREADSHEET REQUIRED IMPORTED_TARGET libspreadsheet)
pkg_check_modules(GOFFICE REQUIRED IMPORTED_TARGET libgoffice-0.10)
pkg_check_modules(GTK REQUIRED IMPORTED_TARGET gtk+-3.0)
pkg_check_modules(GSF REQUIRED IMPORTED_TARGET libgsf-1)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)
pkg_check_modules(GOBJECT REQUIRED IMPORTED_TARGET gobject-2.0)
pkg_check_modules(LIBXML REQUIRED IMPORTED_TARGET libxml-2.0)

add_executable(test_gnumeric test.c)
target_link_libraries(test_gnumeric PRIVATE
    PkgConfig::LIBSPREADSHEET
    PkgConfig::GOFFICE
    PkgConfig::GTK
    PkgConfig::GSF
    PkgConfig::GLIB
    PkgConfig::GOBJECT
    PkgConfig::LIBXML)

enable_testing()
add_test(NAME test_gnumeric COMMAND test_gnumeric)
