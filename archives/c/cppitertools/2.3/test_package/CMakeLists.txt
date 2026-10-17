cmake_minimum_required(VERSION 3.15)
project(test_cppitertools CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cppitertools REQUIRED)

add_executable(test_cppitertools test_cppitertools.cpp)
target_link_libraries(test_cppitertools cppitertools::cppitertools)
target_compile_features(test_cppitertools PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_cppitertools COMMAND test_cppitertools)