cmake_minimum_required(VERSION 3.15)
project(test_logfault CXX)

# Find the package via Conan-generated CMakeDeps
find_package(logfault REQUIRED)

add_executable(test_logfault test.cpp)
target_link_libraries(test_logfault logfault::logfault)

enable_testing()
add_test(NAME test_logfault COMMAND test_logfault)