cmake_minimum_required(VERSION 3.15)
project(test_ots C)

find_package(libots-1 REQUIRED)

add_executable(test_ots test_ots.c)
target_link_libraries(test_ots libots-1::libots-1)

enable_testing()
add_test(NAME test_ots COMMAND test_ots)
