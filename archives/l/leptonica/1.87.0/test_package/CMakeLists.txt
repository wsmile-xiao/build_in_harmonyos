cmake_minimum_required(VERSION 3.15)
project(test_leptonica C)

find_package(leptonica REQUIRED)

add_executable(test_leptonica test.c)
target_link_libraries(test_leptonica leptonica::leptonica)

enable_testing()
add_test(NAME test_leptonica COMMAND test_leptonica)
