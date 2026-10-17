cmake_minimum_required(VERSION 3.15)
project(test_backward-cpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(backward-cpp REQUIRED)

add_executable(test_backward-cpp test.cpp)
target_link_libraries(test_backward-cpp backward-cpp::backward-cpp)

enable_testing()
add_test(NAME test_backward-cpp COMMAND test_backward-cpp)
