cmake_minimum_required(VERSION 3.15)
project(test_caps C)

# Find the package via Conan-generated CMakeDeps
find_package(caps REQUIRED)

add_executable(test_caps test.c)
target_link_libraries(test_caps caps::caps)

enable_testing()
add_test(NAME test_caps COMMAND test_caps)
