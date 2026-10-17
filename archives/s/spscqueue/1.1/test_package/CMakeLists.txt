cmake_minimum_required(VERSION 3.15)
project(test_spscqueue CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find the package via Conan-generated CMakeDeps
find_package(spscqueue REQUIRED)

add_executable(test_spscqueue test_spscqueue.cpp)
target_link_libraries(test_spscqueue spscqueue::spscqueue)

enable_testing()
add_test(NAME test_spscqueue COMMAND test_spscqueue)