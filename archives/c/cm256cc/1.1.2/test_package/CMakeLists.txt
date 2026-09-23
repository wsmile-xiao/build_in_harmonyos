cmake_minimum_required(VERSION 3.15)
project(cm256cc_test_package CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cm256cc CONFIG REQUIRED)

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE cm256cc::cm256cc)

enable_testing()
add_test(NAME consumer COMMAND consumer)
