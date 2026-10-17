cmake_minimum_required(VERSION 3.16)
project(libdetour_test CXX)

find_package(libdetour REQUIRED CONFIG)

add_executable(libdetour_test test_detour.cpp)
target_link_libraries(libdetour_test PRIVATE libdetour::libdetour)
