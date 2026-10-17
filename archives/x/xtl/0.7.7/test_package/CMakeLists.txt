cmake_minimum_required(VERSION 3.15)
project(test_xtl CXX)

find_package(xtl REQUIRED)

add_executable(test_xtl test.cpp)
target_link_libraries(test_xtl PRIVATE xtl)

enable_testing()
add_test(NAME test_xtl COMMAND test_xtl)
