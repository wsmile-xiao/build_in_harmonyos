cmake_minimum_required(VERSION 3.15)
project(test_librcc C)

find_package(librcc REQUIRED)

add_executable(test_librcc test.c)
target_link_libraries(test_librcc librcc::librcc)

enable_testing()
add_test(NAME test_librcc COMMAND test_librcc)
