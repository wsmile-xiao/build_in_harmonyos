cmake_minimum_required(VERSION 3.15)
project(test_gtksourceview4 C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTKSOURCEVIEW4 REQUIRED IMPORTED_TARGET gtksourceview-4)

add_executable(test_gtksourceview4 test_gtksourceview4.c)
target_link_libraries(test_gtksourceview4 PRIVATE PkgConfig::GTKSOURCEVIEW4)
