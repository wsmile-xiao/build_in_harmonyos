cmake_minimum_required(VERSION 3.15)
project(test_duktape C)

# Find the package via Conan-generated CMakeDeps
find_package(duktape REQUIRED)

add_executable(test_duktape test.c)
target_link_libraries(test_duktape duktape::duktape)

enable_testing()
add_test(NAME test_duktape COMMAND test_duktape)
