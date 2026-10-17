cmake_minimum_required(VERSION 3.15)
project(test_topparser C)

find_package(topparser REQUIRED CONFIG)

add_executable(test_topparser test_topparser.c)
target_link_libraries(test_topparser topparser::topparser)
