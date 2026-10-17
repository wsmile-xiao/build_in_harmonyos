cmake_minimum_required(VERSION 3.15)
project(libprintsys_test C)

find_package(libprintsys CONFIG REQUIRED)

add_executable(test_printcap test.c)
target_link_libraries(test_printcap PRIVATE libprintsys::libprintsys)
