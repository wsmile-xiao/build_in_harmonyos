cmake_minimum_required(VERSION 3.15)
project(mozjpeg_test C)

find_package(mozjpeg CONFIG REQUIRED)

add_executable(mozjpeg_functional_test test.c)
target_link_libraries(mozjpeg_functional_test PRIVATE mozjpeg::mozjpeg)

enable_testing()
add_test(NAME mozjpeg_functional_test COMMAND mozjpeg_functional_test)
