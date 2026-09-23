cmake_minimum_required(VERSION 3.15)
project(test_pan CXX)

find_package(PkgConfig REQUIRED)

# Resolve exactly the modules pan requires, the same way its build does.
pkg_check_modules(GMIME REQUIRED IMPORTED_TARGET gmime-3.0)
pkg_check_modules(GTK3 REQUIRED IMPORTED_TARGET gtk+-3.0)

add_executable(test_pan test_pan.cxx)
target_link_libraries(test_pan PRIVATE PkgConfig::GMIME PkgConfig::GTK3)
