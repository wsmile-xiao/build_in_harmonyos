cmake_minimum_required(VERSION 3.15)
project(test_scope_lite CXX)

find_package(scope-lite REQUIRED)

add_executable(test_scope_lite test_scope_lite.cpp)
target_link_libraries(test_scope_lite PRIVATE nonstd::scope-lite)
set_target_properties(test_scope_lite PROPERTIES CXX_STANDARD 11)
