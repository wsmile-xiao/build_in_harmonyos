cmake_minimum_required(VERSION 3.15)
project(test_czmq LANGUAGES C)

find_package(czmq REQUIRED)

add_executable(test_czmq test_czmq.c)
target_link_libraries(test_czmq PRIVATE czmq::czmq)

enable_testing()
add_test(NAME test_czmq COMMAND test_czmq)
