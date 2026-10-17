cmake_minimum_required(VERSION 3.15)
project(test_biosoup CXX)

find_package(biosoup REQUIRED CONFIG)

add_executable(test_biosoup test_biosoup.cpp)
target_link_libraries(test_biosoup biosoup::biosoup)
