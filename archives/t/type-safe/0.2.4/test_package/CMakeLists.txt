cmake_minimum_required(VERSION 3.15)
project(type_safe_test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(type_safe CONFIG REQUIRED)

add_executable(type_safe_consumer test.cpp)
target_link_libraries(type_safe_consumer PRIVATE type_safe::type_safe)

enable_testing()
add_test(NAME type_safe_consumer COMMAND type_safe_consumer)

