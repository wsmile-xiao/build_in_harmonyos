cmake_minimum_required(VERSION 3.5)
project(test_combine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Combine REQUIRED CONFIG)

add_executable(test_combine test_combine.cpp)
target_link_libraries(test_combine PRIVATE Combine::Combine)
