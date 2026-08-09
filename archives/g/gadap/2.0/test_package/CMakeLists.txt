cmake_minimum_required(VERSION 3.15)
project(test_gadap CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gadap REQUIRED)

add_executable(test_gadap test.cc)
target_link_libraries(test_gadap gadap::gadap)

enable_testing()
add_test(NAME test_gadap COMMAND test_gadap)
