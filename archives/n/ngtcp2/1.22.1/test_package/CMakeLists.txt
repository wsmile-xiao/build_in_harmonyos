cmake_minimum_required(VERSION 3.15)
project(test_ngtcp2 C)

find_package(ngtcp2 REQUIRED)

add_executable(test_ngtcp2 test.c)
target_link_libraries(test_ngtcp2 ngtcp2::ngtcp2)

enable_testing()
add_test(NAME test_ngtcp2 COMMAND test_ngtcp2)
