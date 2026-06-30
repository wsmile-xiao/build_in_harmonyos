cmake_minimum_required(VERSION 3.15)
project(test_at C)

# Find the package via Conan-generated CMakeDeps
find_package(at REQUIRED)

# at is a binary-only package; no library to link against
add_executable(test_at test.c)

enable_testing()
add_test(NAME test_at COMMAND test_at)
