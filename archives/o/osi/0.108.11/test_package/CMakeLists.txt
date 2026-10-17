cmake_minimum_required(VERSION 3.15)
project(test_osi CXX)

find_package(osi REQUIRED CONFIG)

add_executable(test_osi test_osi.cpp)
target_link_libraries(test_osi PRIVATE osi::osi)
