cmake_minimum_required(VERSION 3.15)
project(test_fribidi C)

find_package(fribidi REQUIRED)

add_executable(test_fribidi test_fribidi.c)
target_link_libraries(test_fribidi fribidi::fribidi)
