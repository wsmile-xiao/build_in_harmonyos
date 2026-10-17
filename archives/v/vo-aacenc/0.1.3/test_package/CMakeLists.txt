cmake_minimum_required(VERSION 3.15)
project(test_vo_aacenc C)

find_package(vo-aacenc REQUIRED)

add_executable(test_vo_aacenc test.c)
target_link_libraries(test_vo_aacenc vo-aacenc::vo-aacenc)
