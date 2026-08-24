cmake_minimum_required(VERSION 3.15)
project(wv_test LANGUAGES C)

find_package(wv CONFIG REQUIRED)

add_executable(wv_test test.c)
target_link_libraries(wv_test PRIVATE wv::wv)
