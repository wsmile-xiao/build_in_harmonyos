cmake_minimum_required(VERSION 3.15)
project(test_tl CXX)

find_package(tl-expected REQUIRED)

add_executable(test_tl test_tl.cpp)
target_link_libraries(test_tl PRIVATE tl::expected)

enable_testing()
add_test(NAME test_tl COMMAND test_tl)
