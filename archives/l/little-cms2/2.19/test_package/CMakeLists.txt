cmake_minimum_required(VERSION 3.16)
project(test_lcms2 C)

set(CMAKE_C_STANDARD 99)

enable_testing()

find_package(little-cms2 REQUIRED)

add_executable(test_lcms2 src/test_lcms2.c)
target_link_libraries(test_lcms2 little-cms2::little-cms2)
target_link_libraries(test_lcms2 m)

add_test(NAME lcms2_consumer COMMAND test_lcms2)
