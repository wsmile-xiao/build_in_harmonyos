cmake_minimum_required(VERSION 3.15)
project(test_byte_lite CXX)

find_package(byte-lite REQUIRED)

add_executable(test_byte_lite test_byte_lite.cpp)
target_link_libraries(test_byte_lite PRIVATE nonstd::byte-lite)
set_target_properties(test_byte_lite PROPERTIES CXX_STANDARD 17)
