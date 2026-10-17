cmake_minimum_required(VERSION 3.15)
project(test_libheif C)

find_package(libheif REQUIRED)

add_executable(test_libheif test.c)
target_link_libraries(test_libheif libheif::libheif)

enable_testing()
add_test(NAME test_libheif COMMAND test_libheif)
