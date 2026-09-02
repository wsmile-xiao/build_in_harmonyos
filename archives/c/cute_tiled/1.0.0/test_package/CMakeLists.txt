cmake_minimum_required(VERSION 3.15)
project(test_cute_tiled C)

find_package(cute_tiled CONFIG REQUIRED)

add_executable(test_cute_tiled test.c)
target_link_libraries(test_cute_tiled PRIVATE cute_tiled::cute_tiled)
