cmake_minimum_required(VERSION 3.15)
project(test_librest C)

find_package(rest-1.0 CONFIG REQUIRED)

add_executable(test_librest test_librest.c)
target_link_libraries(test_librest PRIVATE rest-1.0::rest-1.0)

enable_testing()
add_test(NAME test_librest COMMAND test_librest)
