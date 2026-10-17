cmake_minimum_required(VERSION 3.15)
project(test_libcoap C)

find_package(libcoap REQUIRED)

add_executable(test_libcoap test_libcoap.c)
target_link_libraries(test_libcoap libcoap::libcoap)
