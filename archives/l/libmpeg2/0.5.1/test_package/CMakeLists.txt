cmake_minimum_required(VERSION 3.15)
project(test_libmpeg2 C)

find_package(libmpeg2 REQUIRED)
add_executable(test_libmpeg2 test.c)
target_link_libraries(test_libmpeg2 PRIVATE libmpeg2::libmpeg2)
