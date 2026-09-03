cmake_minimum_required(VERSION 3.15)
project(test_pystring CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pystring REQUIRED)

add_executable(test_pystring test.cpp)
target_link_libraries(test_pystring pystring::pystring)

enable_testing()
add_test(NAME test_pystring COMMAND test_pystring)
