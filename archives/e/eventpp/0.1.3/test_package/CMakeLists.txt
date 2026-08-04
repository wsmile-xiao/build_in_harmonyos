cmake_minimum_required(VERSION 3.15)
project(test_eventpp CXX)

set(CMAKE_CXX_STANDARD 11)

# Find the package via Conan-generated CMakeDeps
find_package(eventpp REQUIRED)

add_executable(test_eventpp test_eventpp.cpp)
target_link_libraries(test_eventpp eventpp::eventpp)

enable_testing()
add_test(NAME test_eventpp COMMAND test_eventpp)
