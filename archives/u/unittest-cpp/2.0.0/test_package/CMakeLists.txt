cmake_minimum_required(VERSION 3.15)
project(test_unittest_cpp CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(unittest-cpp REQUIRED)

add_executable(test_unittest_cpp test.cpp)
target_link_libraries(test_unittest_cpp PRIVATE unittest-cpp::unittest-cpp)

enable_testing()
add_test(NAME consumer_assertions COMMAND test_unittest_cpp)
