cmake_minimum_required(VERSION 3.15)
project(test_adios2 CXX)

find_package(adios2 REQUIRED CONFIG)

add_executable(test_adios2 test_adios2.cpp)
target_link_libraries(test_adios2 PRIVATE adios2::adios2)
set_target_properties(test_adios2 PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
