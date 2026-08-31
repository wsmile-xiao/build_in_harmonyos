cmake_minimum_required(VERSION 3.15)
project(test_unibilium C)

# Find the package via Conan-generated CMakeDeps
find_package(unibilium REQUIRED)

add_executable(test_unibilium test.c)
target_link_libraries(test_unibilium unibilium::unibilium)

enable_testing()
add_test(NAME test_unibilium COMMAND test_unibilium)
