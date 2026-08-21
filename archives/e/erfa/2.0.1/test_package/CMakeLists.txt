cmake_minimum_required(VERSION 3.15)
project(test_erfa C)

find_package(erfa REQUIRED CONFIG)

add_executable(test_erfa test.c)
target_link_libraries(test_erfa PRIVATE erfa::erfa)
