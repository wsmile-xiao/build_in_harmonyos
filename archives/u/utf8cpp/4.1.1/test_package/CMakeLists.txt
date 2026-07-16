cmake_minimum_required(VERSION 3.15)
project(test_utf8cpp CXX)

find_package(utf8cpp REQUIRED)

add_executable(test_utf8cpp test_utf8cpp.cpp)
target_link_libraries(test_utf8cpp PRIVATE utf8cpp::utf8cpp)
set_target_properties(test_utf8cpp PROPERTIES CXX_STANDARD 17)
