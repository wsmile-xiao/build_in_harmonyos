cmake_minimum_required(VERSION 3.15)
project(test_voro CXX)

find_package(VORO REQUIRED)

add_executable(test_voro test_voro.cpp)
target_link_libraries(test_voro PRIVATE VORO::voro++)
set_target_properties(test_voro PROPERTIES CXX_STANDARD 11)
