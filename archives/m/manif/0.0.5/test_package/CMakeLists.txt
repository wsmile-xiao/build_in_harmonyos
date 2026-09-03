cmake_minimum_required(VERSION 3.15)
project(test_manif CXX)

find_package(manif REQUIRED)

add_executable(test_manif test_manif.cpp)
target_link_libraries(test_manif PRIVATE MANIF::manif)
set_target_properties(test_manif PROPERTIES CXX_STANDARD 11)