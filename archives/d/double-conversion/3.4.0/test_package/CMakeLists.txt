cmake_minimum_required(VERSION 3.15)
project(test_double-conversion CXX)

# Find the package via Conan-generated CMakeDeps
find_package(double-conversion REQUIRED)

add_executable(test_double-conversion test.cpp)
target_link_libraries(test_double-conversion double-conversion::double-conversion)

enable_testing()
add_test(NAME test_double-conversion COMMAND test_double-conversion)
