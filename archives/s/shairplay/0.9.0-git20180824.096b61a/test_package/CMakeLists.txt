cmake_minimum_required(VERSION 3.15)
project(test_shairplay C)

find_package(shairplay CONFIG REQUIRED)
add_executable(test_shairplay test.c)
target_link_libraries(test_shairplay PRIVATE shairplay::shairplay)
