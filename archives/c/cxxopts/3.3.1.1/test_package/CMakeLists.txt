cmake_minimum_required(VERSION 3.15)
project(test_cxxopts CXX)

find_package(cxxopts REQUIRED)

add_executable(test_cxxopts test.cpp)
target_link_libraries(test_cxxopts PRIVATE cxxopts::cxxopts)
