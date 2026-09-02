cmake_minimum_required(VERSION 3.15)
project(forkunion_consumer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(forkunion CONFIG REQUIRED)

add_executable(forkunion_consumer test.cpp)
target_link_libraries(forkunion_consumer PRIVATE forkunion::static)
