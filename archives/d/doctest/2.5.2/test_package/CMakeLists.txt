cmake_minimum_required(VERSION 3.15)
project(test_doctest CXX)

# Find the package via Conan-generated CMakeDeps
find_package(doctest REQUIRED)

add_executable(test_doctest test.cpp)
target_link_libraries(test_doctest doctest::doctest)

enable_testing()
add_test(NAME test_doctest COMMAND test_doctest)
