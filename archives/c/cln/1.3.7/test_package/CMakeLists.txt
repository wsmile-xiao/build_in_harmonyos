cmake_minimum_required(VERSION 3.15)
project(cln_consumer CXX)

find_package(cln REQUIRED)

add_executable(consumer test_package.cpp)
target_link_libraries(consumer PRIVATE cln::cln)
