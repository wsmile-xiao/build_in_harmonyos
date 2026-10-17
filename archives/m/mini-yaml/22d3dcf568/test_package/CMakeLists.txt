cmake_minimum_required(VERSION 3.15)
project(test_mini-yaml CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mini-yaml REQUIRED)

add_executable(test_mini-yaml test.cpp)
target_link_libraries(test_mini-yaml mini-yaml::mini-yaml)

enable_testing()
add_test(NAME test_mini-yaml COMMAND test_mini-yaml)