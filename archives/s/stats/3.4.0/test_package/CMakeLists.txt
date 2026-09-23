cmake_minimum_required(VERSION 3.15)
project(test_stats CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(stats REQUIRED)

add_executable(test_stats test.cpp)
target_link_libraries(test_stats stats::stats)

enable_testing()
add_test(NAME test_stats COMMAND test_stats)
