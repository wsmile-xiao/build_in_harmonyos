cmake_minimum_required(VERSION 3.15)
project(test_glbinding CXX)

# Find the package via Conan-generated CMakeDeps
find_package(glbinding REQUIRED)

add_executable(test_glbinding test.cpp)
target_link_libraries(test_glbinding glbinding::glbinding)

enable_testing()
add_test(NAME test_glbinding COMMAND test_glbinding)
