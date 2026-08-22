cmake_minimum_required(VERSION 3.5)
project(test_tre C)

find_package(tre REQUIRED)

add_executable(test_tre test_tre.c)
target_link_libraries(test_tre PRIVATE tre::tre)

enable_testing()
add_test(NAME test_tre COMMAND test_tre)
