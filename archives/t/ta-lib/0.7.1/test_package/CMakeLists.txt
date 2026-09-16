cmake_minimum_required(VERSION 3.15)
project(test_ta_lib C)

find_package(ta-lib REQUIRED)

add_executable(test_ta_lib test.c)
target_link_libraries(test_ta_lib ta-lib::ta-lib)

enable_testing()
add_test(NAME test_ta_lib COMMAND test_ta_lib)
