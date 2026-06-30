cmake_minimum_required(VERSION 3.15)
project(test_attr C)

# Find the package via Conan-generated CMakeDeps
find_package(attr REQUIRED)

add_executable(test_attr test.c)
target_link_libraries(test_attr attr::attr)

enable_testing()
add_test(NAME test_attr COMMAND test_attr)
