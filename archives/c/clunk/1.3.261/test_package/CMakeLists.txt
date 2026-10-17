cmake_minimum_required(VERSION 3.15)
project(clunk_consumer CXX)

find_package(clunk CONFIG REQUIRED)

add_executable(test_clunk test_clunk.cpp)
target_link_libraries(test_clunk PRIVATE clunk::clunk)
