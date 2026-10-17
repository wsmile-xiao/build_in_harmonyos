cmake_minimum_required(VERSION 3.15)
project(test_ableton_link CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(ableton-link REQUIRED)

add_executable(test_link test_link.cpp)
target_link_libraries(test_link ableton-link::ableton-link)

enable_testing()
add_test(NAME test_link COMMAND test_link)
