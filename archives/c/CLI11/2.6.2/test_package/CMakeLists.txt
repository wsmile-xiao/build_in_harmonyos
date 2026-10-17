cmake_minimum_required(VERSION 3.15)
project(test_cli11 CXX)

find_package(CLI11 REQUIRED)

add_executable(test_cli11 test.cpp)
target_link_libraries(test_cli11 PRIVATE CLI11::CLI11)
set_target_properties(test_cli11 PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)
