cmake_minimum_required(VERSION 3.15)
project(test_fastor CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(fastor REQUIRED)

add_executable(test_fastor test.cpp)
target_link_libraries(test_fastor fastor::fastor)

enable_testing()
add_test(NAME test_fastor COMMAND test_fastor)
