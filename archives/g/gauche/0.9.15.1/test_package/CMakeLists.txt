cmake_minimum_required(VERSION 3.15)
project(test_gauche C)

# Find the package via Conan-generated CMakeDeps
find_package(gauche REQUIRED)

add_executable(test_gauche test.c)
target_link_libraries(test_gauche gauche::gauche)

enable_testing()
add_test(NAME test_gauche COMMAND test_gauche)
