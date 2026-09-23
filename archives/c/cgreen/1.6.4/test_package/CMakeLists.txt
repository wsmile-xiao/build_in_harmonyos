# test_package CMakeLists — 4 NEW consumer executables against packaged
# libcgreen (counts: 4 executables / 17 test functions / 44 assertion calls
# incl. 2 negative-path failure assertions; upstream-reproduced 26 CTest
# entries already run inside the recipe build()).
cmake_minimum_required(VERSION 3.15)
project(test_cgreen C CXX)

find_package(cgreen REQUIRED)

add_executable(test_cgreen_c test_cgreen_c.c)
target_link_libraries(test_cgreen_c PRIVATE cgreen::cgreen)

add_executable(test_cgreen_boundary test_cgreen_boundary.c)
target_link_libraries(test_cgreen_boundary PRIVATE cgreen::cgreen)

add_executable(test_cgreen_failpath test_cgreen_failpath.c)
target_link_libraries(test_cgreen_failpath PRIVATE cgreen::cgreen)

add_executable(test_cgreen_cpp test_cgreen_cpp.cpp)
target_link_libraries(test_cgreen_cpp PRIVATE cgreen::cgreen)
