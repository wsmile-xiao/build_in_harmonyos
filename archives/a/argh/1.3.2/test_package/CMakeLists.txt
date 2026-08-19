cmake_minimum_required(VERSION 3.15)
project(test_argh CXX)

# Find the package via Conan-generated CMakeDeps
find_package(argh REQUIRED)

add_executable(test_argh test.cpp)
target_link_libraries(test_argh argh::argh)

enable_testing()
add_test(NAME test_argh COMMAND test_argh)
