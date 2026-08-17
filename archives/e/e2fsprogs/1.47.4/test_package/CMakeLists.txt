cmake_minimum_required(VERSION 3.15)
project(test_e2fsprogs C)

find_package(e2fsprogs REQUIRED)

add_executable(test_e2fsprogs test.c)
target_link_libraries(test_e2fsprogs e2fsprogs::com_err)

enable_testing()
add_test(NAME test_e2fsprogs COMMAND test_e2fsprogs)
