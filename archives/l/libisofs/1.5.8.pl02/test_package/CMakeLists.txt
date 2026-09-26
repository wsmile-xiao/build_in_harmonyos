cmake_minimum_required(VERSION 3.15)

project(test_libisofs C)

find_package(libisofs CONFIG REQUIRED)

add_executable(test_libisofs test.c)

target_link_libraries(test_libisofs PRIVATE libisofs::libisofs)
