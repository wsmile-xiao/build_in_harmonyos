cmake_minimum_required(VERSION 3.15)
project(test_iguana CXX)

find_package(iguana REQUIRED)

add_executable(test_iguana test_iguana.cpp)
target_link_libraries(test_iguana PRIVATE iguana::iguana)
set_target_properties(test_iguana PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)
