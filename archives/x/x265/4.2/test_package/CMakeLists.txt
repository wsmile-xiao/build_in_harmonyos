cmake_minimum_required(VERSION 3.15)
project(test_x265 C)

find_package(x265 REQUIRED)

add_executable(test_x265 test.c)
target_link_libraries(test_x265 x265::x265)

enable_testing()
add_test(NAME test_x265 COMMAND test_x265)
