cmake_minimum_required(VERSION 3.15)
project(test_ndpi C)

find_package(ndpi REQUIRED)

add_executable(test_ndpi test.c)
target_link_libraries(test_ndpi ndpi::ndpi)

enable_testing()
add_test(NAME test_ndpi COMMAND test_ndpi)
