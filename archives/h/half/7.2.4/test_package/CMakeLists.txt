cmake_minimum_required(VERSION 3.15)
project(test_half CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Resolve the packaged half header through the Conan-generated CMakeDeps config
find_package(half REQUIRED CONFIG)

add_executable(test_half test_half.cpp)
target_link_libraries(test_half half::half)

enable_testing()
add_test(NAME test_half COMMAND test_half)
