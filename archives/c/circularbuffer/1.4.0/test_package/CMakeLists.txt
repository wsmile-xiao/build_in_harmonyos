cmake_minimum_required(VERSION 3.15)
project(test_circularbuffer CXX)

# Find the package via Conan-generated CMakeDeps
find_package(circularbuffer REQUIRED)

add_executable(test_circularbuffer test.cpp)
target_link_libraries(test_circularbuffer circularbuffer::circularbuffer)

enable_testing()
add_test(NAME test_circularbuffer COMMAND test_circularbuffer)
