cmake_minimum_required(VERSION 3.15)
project(test_cunit C)

find_package(cunit REQUIRED CONFIG)

add_executable(test_cunit test.c)
target_link_libraries(test_cunit cunit::cunit)

enable_testing()
add_test(NAME test_cunit COMMAND test_cunit)