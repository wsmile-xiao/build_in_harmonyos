cmake_minimum_required(VERSION 3.15)
project(test_libsais C)

find_package(libsais REQUIRED)

add_executable(test_libsais test.c)
target_link_libraries(test_libsais libsais::libsais)

enable_testing()
add_test(NAME test_libsais COMMAND test_libsais)
