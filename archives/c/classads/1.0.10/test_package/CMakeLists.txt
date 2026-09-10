cmake_minimum_required(VERSION 3.15)
project(classads_consumer CXX)

find_package(classads REQUIRED)

add_executable(consumer test_package.cpp)
target_link_libraries(consumer PRIVATE classads::classads)
