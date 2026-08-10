cmake_minimum_required(VERSION 3.15)
project(test_ale C)

# Find the package via Conan-generated CMakeDeps
# Note: ale is an application package (no library target), so we only
# verify the package is found and run the ale-bin binary via test.c.
find_package(ale REQUIRED)

add_executable(test_ale test.c)

enable_testing()
add_test(NAME test_ale COMMAND test_ale)