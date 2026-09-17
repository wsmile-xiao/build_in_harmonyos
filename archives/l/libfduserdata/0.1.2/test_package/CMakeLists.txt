cmake_minimum_required(VERSION 3.15)

project(test_libfduserdata C)

find_package(fduserdata CONFIG REQUIRED)

add_executable(test_libfduserdata test.c)

target_link_libraries(test_libfduserdata PRIVATE fduserdata::fduserdata)

enable_testing()
add_test(NAME test_libfduserdata COMMAND test_libfduserdata)
