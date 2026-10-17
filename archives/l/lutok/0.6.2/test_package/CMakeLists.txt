cmake_minimum_required(VERSION 3.15)
project(test_lutok CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(lutok REQUIRED)

add_executable(test_lutok test_lutok.cpp)
target_link_libraries(test_lutok PRIVATE lutok::lutok)
