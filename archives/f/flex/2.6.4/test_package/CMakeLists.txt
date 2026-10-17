cmake_minimum_required(VERSION 3.15)
project(test_flex C)

# Find the package via Conan-generated CMakeDeps
find_package(flex REQUIRED)

add_executable(test_flex test.c)
target_link_libraries(test_flex flex::flex)

enable_testing()
add_test(NAME test_flex COMMAND test_flex)
