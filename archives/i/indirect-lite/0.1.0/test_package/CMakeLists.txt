cmake_minimum_required(VERSION 3.15)
project(test_indirect_lite CXX)

find_package(indirect-value-lite REQUIRED)

add_executable(test_indirect_lite test_indirect_lite.cpp)
target_link_libraries(test_indirect_lite PRIVATE nonstd::indirect-value-lite)
set_target_properties(test_indirect_lite PROPERTIES CXX_STANDARD 17)