cmake_minimum_required(VERSION 3.15)
project(test_libfido2 C)

find_package(fido2 REQUIRED)

add_executable(test_libfido2 test.c)
target_link_libraries(test_libfido2 PRIVATE fido2::fido2)
