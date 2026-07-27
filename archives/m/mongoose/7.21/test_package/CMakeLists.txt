cmake_minimum_required(VERSION 3.15)
project(test_mongoose C)

find_package(mongoose REQUIRED)

add_executable(test_mongoose test.c)
target_link_libraries(test_mongoose mongoose::mongoose)

enable_testing()
add_test(NAME test_mongoose COMMAND test_mongoose)
