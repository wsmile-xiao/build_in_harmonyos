cmake_minimum_required(VERSION 3.15)
project(test_libyajl C)

find_package(yajl REQUIRED)

add_executable(test_libyajl test.c)
target_link_libraries(test_libyajl libyajl::libyajl)

enable_testing()
add_test(NAME test_libyajl COMMAND test_libyajl)
