cmake_minimum_required(VERSION 3.15)
project(test_editline C)

# Find the package via Conan-generated CMakeDeps
find_package(editline REQUIRED)

add_executable(test_editline test.c)
target_link_libraries(test_editline editline::editline)

enable_testing()
add_test(NAME test_editline COMMAND test_editline)
