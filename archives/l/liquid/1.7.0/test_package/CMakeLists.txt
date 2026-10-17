cmake_minimum_required(VERSION 3.15)
project(test_liquid C)

find_package(liquid REQUIRED)

add_executable(test_liquid test.c)
target_link_libraries(test_liquid liquid::liquid)

enable_testing()
add_test(NAME test_liquid COMMAND test_liquid)
