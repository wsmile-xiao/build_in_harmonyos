cmake_minimum_required(VERSION 3.15)
project(test_bit_lite CXX)

find_package(bit-lite REQUIRED)

add_executable(test_bit_lite test_bit_lite.cpp)
target_link_libraries(test_bit_lite PRIVATE nonstd::bit-lite)
set_target_properties(test_bit_lite PROPERTIES CXX_STANDARD 17)