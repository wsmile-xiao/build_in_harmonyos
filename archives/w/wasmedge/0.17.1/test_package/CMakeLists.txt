cmake_minimum_required(VERSION 3.15)
project(test_wasmedge C CXX)

find_package(wasmedge REQUIRED)

add_executable(test_wasmedge test_wasmedge.c)
set_target_properties(test_wasmedge PROPERTIES LINKER_LANGUAGE CXX)
target_link_libraries(test_wasmedge wasmedge::wasmedge)
