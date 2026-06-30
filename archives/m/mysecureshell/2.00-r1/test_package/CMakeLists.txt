cmake_minimum_required(VERSION 3.15)
project(test_mysecureshell C)

# Find the package via Conan-generated CMakeDeps
find_package(mysecureshell REQUIRED)

add_executable(test_mysecureshell test.c)
target_link_libraries(test_mysecureshell mysecureshell::mysecureshell)

enable_testing()
add_test(NAME test_mysecureshell COMMAND test_mysecureshell)
