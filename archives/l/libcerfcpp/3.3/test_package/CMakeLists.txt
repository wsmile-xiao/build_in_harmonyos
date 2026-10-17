cmake_minimum_required(VERSION 3.15)
project(test_libcerfcpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cerf REQUIRED CONFIG)

add_executable(test_cerfcpp test_cerfcpp.cpp)
target_link_libraries(test_cerfcpp cerf::cerfcpp)

enable_testing()
add_test(NAME test_cerfcpp COMMAND test_cerfcpp)
