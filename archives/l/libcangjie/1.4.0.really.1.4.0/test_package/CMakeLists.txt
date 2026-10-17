cmake_minimum_required(VERSION 3.15)
project(test_libcangjie C)

find_package(libcangjie REQUIRED)

add_executable(test_libcangjie test_cangjie.c)
target_link_libraries(test_libcangjie libcangjie::cangjie)

enable_testing()
add_test(NAME test_libcangjie COMMAND test_libcangjie)
