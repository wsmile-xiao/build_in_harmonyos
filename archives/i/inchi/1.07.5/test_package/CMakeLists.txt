cmake_minimum_required(VERSION 3.15)
project(test_inchi C)

find_package(inchi CONFIG REQUIRED)

add_executable(test_inchi test_inchi.c)
target_link_libraries(test_inchi PRIVATE inchi::inchi)
