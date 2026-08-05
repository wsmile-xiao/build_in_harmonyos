cmake_minimum_required(VERSION 3.15)
project(test_libassuan C)

find_package(libassuan CONFIG REQUIRED)

add_executable(test_libassuan test.c)
target_link_libraries(test_libassuan PRIVATE libassuan::libassuan)
