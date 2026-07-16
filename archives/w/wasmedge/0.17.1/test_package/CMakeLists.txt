cmake_minimum_required(VERSION 3.15)
project(test_wasmedge C)

find_package(wasmedge REQUIRED)

add_executable(test_wasmedge test_wasmedge.c)
target_link_libraries(test_wasmedge wasmedge::wasmedge)
