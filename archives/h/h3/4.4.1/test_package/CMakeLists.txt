cmake_minimum_required(VERSION 3.15)
project(test_h3 C)

# Find the package via Conan-generated CMakeDeps
find_package(h3 REQUIRED)

add_executable(test_h3 test.c)
target_link_libraries(test_h3 h3::h3)

enable_testing()
add_test(NAME test_h3 COMMAND test_h3)
