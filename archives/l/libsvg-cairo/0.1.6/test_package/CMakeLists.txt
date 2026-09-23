cmake_minimum_required(VERSION 3.15)
project(test_package C)

# svg-cairo.h includes svg.h and cairo.h directly, so the consumer needs
# the headers of both public dependencies next to the package itself.
# (Same pattern as the cairomm/1.16.2 test_package in this repo.)
find_package(libsvg-cairo CONFIG REQUIRED)
find_package(libsvg CONFIG REQUIRED)
find_package(cairo CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE
    libsvg-cairo::libsvg-cairo
    libsvg::libsvg
    cairo::cairo)

enable_testing()
add_test(NAME test_package COMMAND test_package)
