cmake_minimum_required(VERSION 3.15)
project(test_aravis C)

find_package(aravis REQUIRED CONFIG)

add_executable(test_aravis test_aravis.c)
target_link_libraries(test_aravis PRIVATE aravis::aravis)
