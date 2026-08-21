cmake_minimum_required(VERSION 3.15)
project(test_base16384 C)

find_package(base16384 REQUIRED)

add_executable(test_base16384 test.c)
target_link_libraries(test_base16384 base16384::base16384)

enable_testing()
add_test(NAME test_base16384 COMMAND test_base16384)
