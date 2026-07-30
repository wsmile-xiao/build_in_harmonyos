cmake_minimum_required(VERSION 3.15)
project(test_xsimd CXX)

find_package(xsimd REQUIRED)

add_executable(test_xsimd test.cpp)
target_link_libraries(test_xsimd PRIVATE xsimd)

enable_testing()
add_test(NAME test_xsimd COMMAND test_xsimd)
