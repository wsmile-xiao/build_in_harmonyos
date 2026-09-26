cmake_minimum_required(VERSION 3.15)
project(meschach_test LANGUAGES C)

find_package(meschach CONFIG REQUIRED)
add_executable(meschach_test test.c)
target_link_libraries(meschach_test PRIVATE meschach::meschach)
