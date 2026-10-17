cmake_minimum_required(VERSION 3.15)
project(test_mbedtls C)

find_package(mbedtls REQUIRED)

add_executable(test_mbedtls test.c)
target_link_libraries(test_mbedtls mbedtls::mbedtls)

enable_testing()
add_test(NAME test_mbedtls COMMAND test_mbedtls)
