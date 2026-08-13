cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(Eigen3 REQUIRED)

add_executable(test_eigen test.cpp)
target_link_libraries(test_eigen PRIVATE Eigen3::Eigen)
set_property(TARGET test_eigen PROPERTY CXX_STANDARD 11)