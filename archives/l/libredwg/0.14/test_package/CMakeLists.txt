cmake_minimum_required(VERSION 3.15)
project(test_libredwg C)

find_package(libredwg REQUIRED)

add_executable(test_libredwg test.c)
target_link_libraries(test_libredwg libredwg::libredwg)

enable_testing()
add_test(NAME test_libredwg COMMAND test_libredwg)
