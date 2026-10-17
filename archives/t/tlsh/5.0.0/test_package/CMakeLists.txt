cmake_minimum_required(VERSION 3.15)
project(test_tlsh CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(tlsh REQUIRED)

add_executable(test_tlsh test_tlsh.cpp)
target_link_libraries(test_tlsh PRIVATE tlsh::tlsh)
