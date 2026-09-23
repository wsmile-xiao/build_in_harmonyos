cmake_minimum_required(VERSION 3.16)
project(test_corrade CXX)

find_package(Corrade REQUIRED COMPONENTS Utility Containers)

add_executable(test_corrade test.cpp)
target_link_libraries(test_corrade PRIVATE Corrade::Utility Corrade::Containers)