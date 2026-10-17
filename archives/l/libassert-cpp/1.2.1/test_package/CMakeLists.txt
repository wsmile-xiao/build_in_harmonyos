cmake_minimum_required(VERSION 3.15)
project(test_libassert_cpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(assert REQUIRED CONFIG)

add_executable(test_libassert_cpp test.cpp)
target_link_libraries(test_libassert_cpp assert::assert)

enable_testing()
add_test(NAME test_libassert_cpp COMMAND test_libassert_cpp)