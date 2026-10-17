cmake_minimum_required(VERSION 3.18)
project(test_liblouis C)

find_package(liblouis CONFIG REQUIRED)
add_executable(test_liblouis test_liblouis.c)
target_link_libraries(test_liblouis PRIVATE liblouis::liblouis)
