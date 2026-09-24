cmake_minimum_required(VERSION 3.15)
project(test_libfakekey C)

find_package(libfakekey CONFIG REQUIRED)

add_executable(test_libfakekey test.c)
target_link_libraries(test_libfakekey PRIVATE libfakekey::libfakekey)
