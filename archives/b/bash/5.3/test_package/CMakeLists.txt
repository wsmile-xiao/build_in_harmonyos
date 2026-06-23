cmake_minimum_required(VERSION 3.15)
project(test_bash C)

# Find the package via Conan-generated CMakeDeps
find_package(bash REQUIRED)

add_executable(test_bash test.c)
target_link_libraries(test_bash bash::bash)

enable_testing()
add_test(NAME test_bash COMMAND test_bash)
