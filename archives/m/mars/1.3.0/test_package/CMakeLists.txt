cmake_minimum_required(VERSION 3.16)
project(test_mars CXX)

find_package(mars REQUIRED)

add_executable(test_mars test_mars.cc)
target_link_libraries(test_mars PRIVATE mars::mars pthread)
