cmake_minimum_required(VERSION 3.15)
project(libdca_test LANGUAGES C)

find_package(libdca CONFIG REQUIRED)
add_executable(libdca_test test.c)
target_link_libraries(libdca_test PRIVATE libdca::libdca)
