cmake_minimum_required(VERSION 3.15)
project(test_expected_lite CXX)

find_package(expected-lite REQUIRED)

add_executable(test_expected_lite test_expected_lite.cpp)
target_link_libraries(test_expected_lite PRIVATE nonstd::expected-lite)
set_target_properties(test_expected_lite PROPERTIES CXX_STANDARD 17)
