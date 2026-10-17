cmake_minimum_required(VERSION 3.15)
project(test_librtmp C)

find_package(librtmp REQUIRED)

add_executable(test_librtmp test_librtmp.c)
target_link_libraries(test_librtmp librtmp::librtmp)

enable_testing()
add_test(NAME test_librtmp COMMAND test_librtmp)
