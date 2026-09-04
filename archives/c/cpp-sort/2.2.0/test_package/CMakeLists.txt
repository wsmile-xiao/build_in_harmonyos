cmake_minimum_required(VERSION 3.15)
project(test_cpp-sort LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(cpp-sort REQUIRED)

add_executable(test_cpp-sort test.cpp)
target_link_libraries(test_cpp-sort cpp-sort::cpp-sort)

enable_testing()
add_test(NAME test_cpp-sort COMMAND test_cpp-sort)