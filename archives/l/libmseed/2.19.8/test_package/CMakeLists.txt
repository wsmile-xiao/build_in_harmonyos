cmake_minimum_required(VERSION 3.15)
project(test_libmseed C)

find_package(libmseed REQUIRED)

add_executable(test_libmseed test_libmseed.c)
target_link_libraries(test_libmseed libmseed::libmseed)

enable_testing()
add_test(NAME test_libmseed COMMAND test_libmseed)
