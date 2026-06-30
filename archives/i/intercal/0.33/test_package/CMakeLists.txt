cmake_minimum_required(VERSION 3.15)
project(test_intercal C)

# Find the package via Conan-generated CMakeDeps
find_package(intercal REQUIRED)

add_executable(test_intercal test.c)
target_link_libraries(test_intercal intercal::intercal)

enable_testing()
add_test(NAME test_intercal COMMAND test_intercal)
