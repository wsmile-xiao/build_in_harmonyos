cmake_minimum_required(VERSION 3.15)
project(a52dec_test LANGUAGES C)

find_package(a52dec CONFIG REQUIRED)
add_executable(a52dec_test test.c)
target_link_libraries(a52dec_test PRIVATE a52dec::a52dec)
