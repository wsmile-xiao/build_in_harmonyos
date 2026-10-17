cmake_minimum_required(VERSION 3.15)
project(test_gtksourceview C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTKSOURCEVIEW REQUIRED IMPORTED_TARGET gtksourceview-3.0)

add_executable(test_gtksourceview test_gtksourceview.c)
target_link_libraries(test_gtksourceview PRIVATE PkgConfig::GTKSOURCEVIEW)
