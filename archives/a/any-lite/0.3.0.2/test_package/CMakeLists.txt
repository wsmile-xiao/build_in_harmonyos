cmake_minimum_required(VERSION 3.15)
project(test_any_lite CXX)

find_package(any-lite REQUIRED)

add_executable(test_any_lite test_any_lite.cpp)
target_link_libraries(test_any_lite PRIVATE nonstd::any-lite)
set_target_properties(test_any_lite PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)

# C++11 has no std::any, so this consumer must use the nonstd backport implementation.
add_executable(test_any_lite_cpp11 test_any_lite_cpp11.cpp)
target_link_libraries(test_any_lite_cpp11 PRIVATE nonstd::any-lite)
set_target_properties(test_any_lite_cpp11 PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)
