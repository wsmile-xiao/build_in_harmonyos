cmake_minimum_required(VERSION 3.15)
project(test_libkcapi C)

find_package(libkcapi REQUIRED)

add_executable(test_libkcapi test.c)
target_link_libraries(test_libkcapi PRIVATE libkcapi::libkcapi)
