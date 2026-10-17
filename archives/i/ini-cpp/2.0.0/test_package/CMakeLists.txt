cmake_minimum_required(VERSION 3.10)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ini-cpp REQUIRED)

add_executable(sample sample.cpp)
target_link_libraries(sample ini-cpp::ini-cpp)

enable_testing()
add_test(NAME sample COMMAND sample)
