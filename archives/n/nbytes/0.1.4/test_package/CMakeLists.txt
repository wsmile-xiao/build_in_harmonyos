cmake_minimum_required(VERSION 3.15)
project(test_nbytes CXX)

find_package(nbytes CONFIG REQUIRED)

add_executable(test_nbytes test.cpp)
target_link_libraries(test_nbytes PRIVATE nbytes::nbytes)
set_target_properties(test_nbytes PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
