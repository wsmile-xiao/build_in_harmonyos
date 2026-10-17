cmake_minimum_required(VERSION 3.15)
project(test_cityhash CXX)

find_package(cityhash REQUIRED CONFIG)

add_executable(test_cityhash test_cityhash.cpp)
target_link_libraries(test_cityhash PRIVATE cityhash::cityhash)
