cmake_minimum_required(VERSION 3.15)
project(test_oscpack CXX)

# Find the package via Conan-generated CMakeDeps
find_package(oscpack REQUIRED)

add_executable(test_oscpack test_oscpack.cpp)
target_link_libraries(test_oscpack oscpack::oscpack)

enable_testing()
add_test(NAME test_oscpack COMMAND test_oscpack)
