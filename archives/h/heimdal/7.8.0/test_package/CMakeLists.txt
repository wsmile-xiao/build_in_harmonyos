cmake_minimum_required(VERSION 3.16)
project(test_heimdal C)

find_package(heimdal CONFIG REQUIRED)

add_executable(test_heimdal test.c)
target_link_libraries(test_heimdal PRIVATE heimdal::heimdal)
