cmake_minimum_required(VERSION 3.15)
project(libopennet_test C)

find_package(libopennet REQUIRED)

add_executable(libopennet-test test.c)
target_link_libraries(libopennet-test PRIVATE libopennet::libopennet)
