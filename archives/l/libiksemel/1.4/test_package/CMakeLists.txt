cmake_minimum_required(VERSION 3.15)

project(test_libiksemel C)

find_package(libiksemel CONFIG REQUIRED)

add_executable(test_libiksemel test.c)

target_link_libraries(test_libiksemel PRIVATE libiksemel::libiksemel)
