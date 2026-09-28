cmake_minimum_required(VERSION 3.15)
project(test_qoa C)

find_package(qoa REQUIRED)

add_executable(test_qoa test_qoa.c)
target_link_libraries(test_qoa PRIVATE qoa::qoa)

enable_testing()
add_test(NAME test_qoa COMMAND test_qoa)
