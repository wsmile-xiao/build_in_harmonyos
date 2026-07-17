cmake_minimum_required(VERSION 3.15)
project(test_stp)

find_package(stp REQUIRED)

add_executable(test_stp test.cpp)
target_link_libraries(test_stp stp::stp)
