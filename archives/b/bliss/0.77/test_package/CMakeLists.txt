cmake_minimum_required(VERSION 3.16)
project(test_bliss CXX)

find_package(Bliss REQUIRED)

add_executable(test_bliss test.cpp)
target_link_libraries(test_bliss PRIVATE Bliss::libbliss)
