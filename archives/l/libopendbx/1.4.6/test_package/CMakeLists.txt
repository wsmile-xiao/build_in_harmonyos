cmake_minimum_required(VERSION 3.15)
project(opendbx_test LANGUAGES C)

find_package(libopendbx CONFIG REQUIRED)
add_executable(opendbx_test test.c)
target_link_libraries(opendbx_test PRIVATE libopendbx::libopendbx)
