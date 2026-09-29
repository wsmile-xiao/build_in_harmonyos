cmake_minimum_required(VERSION 3.15)
project(hamlib_test LANGUAGES C)

find_package(hamlib CONFIG REQUIRED)
add_executable(hamlib_test test.c)
target_link_libraries(hamlib_test PRIVATE hamlib::hamlib)
