cmake_minimum_required(VERSION 3.15)
project(test_libportal_gtk3 C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBPORTAL_GTK3 REQUIRED IMPORTED_TARGET libportal-gtk3)
pkg_check_modules(GTK3 REQUIRED IMPORTED_TARGET gtk+-3.0)

add_executable(test_libportal_gtk3 test.c)
target_link_libraries(test_libportal_gtk3 PkgConfig::LIBPORTAL_GTK3 PkgConfig::GTK3)

enable_testing()
add_test(NAME test_libportal_gtk3 COMMAND test_libportal_gtk3)
