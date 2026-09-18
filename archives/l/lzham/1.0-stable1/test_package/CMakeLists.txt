cmake_minimum_required(VERSION 3.15)
project(test_lzham CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lzham REQUIRED)

add_executable(test_lzham test.cpp)
target_link_libraries(test_lzham lzham::lzham)

enable_testing()
add_test(NAME test_lzham COMMAND test_lzham)