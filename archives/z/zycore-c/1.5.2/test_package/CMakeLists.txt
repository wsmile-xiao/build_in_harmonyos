cmake_minimum_required(VERSION 3.15)
project(test_zycore_c C)

find_package(zycore CONFIG REQUIRED)

add_executable(test_zycore_c test.c)
target_link_libraries(test_zycore_c PRIVATE Zycore::Zycore)
