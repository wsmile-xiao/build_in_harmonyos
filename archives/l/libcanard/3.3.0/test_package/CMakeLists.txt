cmake_minimum_required(VERSION 3.15)

project(test_libcanard C)

find_package(canard CONFIG REQUIRED)

add_executable(test_libcanard test.c)

target_link_libraries(test_libcanard PRIVATE canard::canard)

enable_testing()
add_test(NAME test_libcanard COMMAND test_libcanard)
