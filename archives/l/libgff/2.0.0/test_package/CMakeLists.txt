cmake_minimum_required(VERSION 3.15)
project(test_libgff CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libgff REQUIRED)

add_executable(test_libgff test_libgff.cpp)
target_link_libraries(test_libgff libgff::libgff)
