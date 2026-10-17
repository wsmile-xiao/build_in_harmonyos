cmake_minimum_required(VERSION 3.15)
project(test_minctest C)

find_package(minctest REQUIRED CONFIG)

add_executable(test_minctest test_minctest.c)
target_link_libraries(test_minctest minctest::minctest)

enable_testing()
add_test(NAME test_minctest COMMAND test_minctest)
