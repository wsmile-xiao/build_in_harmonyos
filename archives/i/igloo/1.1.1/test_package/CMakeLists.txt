cmake_minimum_required(VERSION 3.15)
project(test_igloo CXX)

find_package(igloo REQUIRED)

add_executable(test_igloo test.cpp)
target_link_libraries(test_igloo igloo::igloo)

enable_testing()
add_test(NAME test_igloo COMMAND test_igloo)