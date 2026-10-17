cmake_minimum_required(VERSION 3.15)
project(test_smashtable CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(smashtable REQUIRED)

add_executable(test_smashtable main.cpp)
target_link_libraries(test_smashtable smashtable::smashtable)
