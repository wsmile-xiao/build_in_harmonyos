cmake_minimum_required(VERSION 3.15)
project(test_cctools C)

find_package(cctools REQUIRED)

add_executable(test_cctools test.c)
target_link_libraries(test_cctools PRIVATE cctools::cctools)
