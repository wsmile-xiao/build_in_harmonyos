cmake_minimum_required(VERSION 3.15)
project(test_libspandsp C)

find_package(spandsp REQUIRED CONFIG)

add_executable(test_libspandsp test_libspandsp.c)
target_link_libraries(test_libspandsp PRIVATE spandsp::spandsp)
