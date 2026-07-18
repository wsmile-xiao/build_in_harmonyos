cmake_minimum_required(VERSION 3.15)
project(test_luv)

find_package(luv REQUIRED)

add_executable(test_luv test.cpp)
target_link_libraries(test_luv luv::luv)
