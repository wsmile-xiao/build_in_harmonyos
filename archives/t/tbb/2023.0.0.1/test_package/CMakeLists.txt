cmake_minimum_required(VERSION 3.15)
project(test_tbb CXX)

find_package(TBB REQUIRED)

add_executable(test_tbb test_tbb.cpp)
target_link_libraries(test_tbb PRIVATE tbb::tbb)
