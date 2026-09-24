cmake_minimum_required(VERSION 3.15)
project(test_cpp-channel CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find the package via Conan-generated CMakeDeps
find_package(cpp-channel REQUIRED)

add_executable(test_cpp-channel test.cpp)
target_link_libraries(test_cpp-channel cpp-channel::cpp-channel)

enable_testing()
add_test(NAME test_cpp-channel COMMAND test_cpp-channel)