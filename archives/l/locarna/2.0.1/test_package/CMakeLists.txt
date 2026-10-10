cmake_minimum_required(VERSION 3.15)
project(test_liblocarna CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(locarna CONFIG REQUIRED)

add_executable(test_liblocarna test_liblocarna.cpp)
target_link_libraries(test_liblocarna PRIVATE locarna::locarna)
