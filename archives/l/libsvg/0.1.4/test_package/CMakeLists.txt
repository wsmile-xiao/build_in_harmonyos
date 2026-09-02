cmake_minimum_required(VERSION 3.15)
project(libsvg_test LANGUAGES C)

find_package(libsvg CONFIG REQUIRED)
add_executable(libsvg_test test.c)
target_link_libraries(libsvg_test PRIVATE libsvg::libsvg)
