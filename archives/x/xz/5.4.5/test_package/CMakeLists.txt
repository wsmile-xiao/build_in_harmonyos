cmake_minimum_required(VERSION 3.15)
project(test_xz C)

# Find the package via Conan-generated CMakeDeps
find_package(xz REQUIRED)

add_executable(test_xz test.c)
target_link_libraries(test_xz xz::xz)

enable_testing()
add_test(NAME test_xz COMMAND test_xz)
