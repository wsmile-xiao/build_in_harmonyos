cmake_minimum_required(VERSION 3.15)
project(test_libxi C)

find_package(libxi REQUIRED)

add_executable(test_libxi test.c)
target_link_libraries(test_libxi PRIVATE libxi::libxi)

enable_testing()
add_test(NAME test_libxi COMMAND test_libxi)
