cmake_minimum_required(VERSION 3.15)
project(test_fossa C)

find_package(fossa REQUIRED)

add_executable(test_fossa test.c)
target_link_libraries(test_fossa fossa::fossa)

enable_testing()
add_test(NAME test_fossa COMMAND test_fossa)
