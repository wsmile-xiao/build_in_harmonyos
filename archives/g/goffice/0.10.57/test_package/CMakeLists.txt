cmake_minimum_required(VERSION 3.15)
project(test_goffice C)

# goffice 是 autotools 库，通过 pkg-config 发现（PkgConfigDeps 生成 .pc）。
# goffice.h 会展开包含 gtk/cairo/pango/gsf/glib 头文件，故显式声明这些模块。
find_package(PkgConfig REQUIRED)
pkg_check_modules(GOFFICE REQUIRED IMPORTED_TARGET libgoffice-0.10)
pkg_check_modules(GTK REQUIRED IMPORTED_TARGET gtk+-3.0)
# 兜底：过滤 PkgConfig::GTK 中实际不存在的 include 路径。cmd-pkgs 预编译
# gtk+-3.0.pc 的依赖链可能把 cairo 解析到硬编码前缀 /usr/local/include/cairo
# （cairo 实际由 conan 依赖提供），该路径不存在时 cmake pkg_check_modules
# 会严格校验并 fatal。这里只保留真实存在的路径。
get_target_property(_gtk_incs PkgConfig::GTK INTERFACE_INCLUDE_DIRECTORIES)
if(_gtk_incs)
    set(_gtk_incs_ok "")
    foreach(_inc IN LISTS _gtk_incs)
        if(EXISTS "${_inc}")
            list(APPEND _gtk_incs_ok "${_inc}")
        endif()
    endforeach()
    set_property(TARGET PkgConfig::GTK PROPERTY INTERFACE_INCLUDE_DIRECTORIES "${_gtk_incs_ok}")
endif()
pkg_check_modules(GSF REQUIRED IMPORTED_TARGET libgsf-1)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)
pkg_check_modules(GOBJECT REQUIRED IMPORTED_TARGET gobject-2.0)
pkg_check_modules(LIBXML REQUIRED IMPORTED_TARGET libxml-2.0)

add_executable(test_goffice test.c)
target_link_libraries(test_goffice PRIVATE
    PkgConfig::GOFFICE
    PkgConfig::GTK
    PkgConfig::GSF
    PkgConfig::GLIB
    PkgConfig::GOBJECT
    PkgConfig::LIBXML)

enable_testing()
add_test(NAME test_goffice COMMAND test_goffice)
