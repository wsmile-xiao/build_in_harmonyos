cmake_minimum_required(VERSION 3.15)
project(test_cxxtools CXX)

find_package(cxxtools REQUIRED CONFIG)

add_executable(test_cxxtools test_cxxtools.cpp)
target_link_libraries(test_cxxtools
    cxxtools::cxxtools
)

enable_testing()
add_test(NAME test_cxxtools COMMAND test_cxxtools)
