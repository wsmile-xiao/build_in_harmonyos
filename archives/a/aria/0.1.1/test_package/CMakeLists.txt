cmake_minimum_required(VERSION 3.15)
project(test_aria C)

find_package(aria CONFIG REQUIRED)

add_executable(test_aria test.c)
target_link_libraries(test_aria PRIVATE aria::aria)

enable_testing()
add_test(NAME test_aria COMMAND test_aria)
