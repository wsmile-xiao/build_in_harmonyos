cmake_minimum_required(VERSION 3.15)
project(test_roxterm C)

# Find the package via Conan-generated CMakeDeps
find_package(roxterm REQUIRED)

add_executable(test_roxterm test.c)
target_link_libraries(test_roxterm roxterm::roxterm)

enable_testing()
add_test(NAME test_roxterm COMMAND test_roxterm)
