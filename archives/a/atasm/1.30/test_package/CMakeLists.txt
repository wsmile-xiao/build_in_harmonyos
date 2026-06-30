cmake_minimum_required(VERSION 3.15)
project(test_atasm C)

# Find the package via Conan-generated CMakeDeps
find_package(atasm REQUIRED)

add_executable(test_atasm test.c)
target_link_libraries(test_atasm atasm::atasm)

enable_testing()
add_test(NAME test_atasm COMMAND test_atasm)
