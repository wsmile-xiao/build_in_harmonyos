cmake_minimum_required(VERSION 3.15)
project(test_cheapglk C)

find_package(cheapglk REQUIRED)

add_executable(test_cheapglk test.c)
target_link_libraries(test_cheapglk cheapglk::cheapglk)

enable_testing()
add_test(NAME test_cheapglk COMMAND test_cheapglk)