cmake_minimum_required(VERSION 3.15)
project(test_libitl C)

find_package(libitl REQUIRED)

add_executable(test_libitl test.c)
target_link_libraries(test_libitl libitl::libitl)

enable_testing()
add_test(NAME test_libitl COMMAND test_libitl)
