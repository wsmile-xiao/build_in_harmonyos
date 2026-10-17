cmake_minimum_required(VERSION 3.15)
project(test_boolean_lite CXX)

find_package(boolean-lite REQUIRED)

add_executable(test_boolean_lite test_boolean_lite.cpp)
target_link_libraries(test_boolean_lite PRIVATE nonstd::boolean-lite)
set_target_properties(test_boolean_lite PROPERTIES CXX_STANDARD 17)
