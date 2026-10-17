cmake_minimum_required(VERSION 3.15)
project(test_liblxi C)

# Find the package via Conan-generated CMakeDeps
find_package(liblxi REQUIRED)

add_executable(test_liblxi test.c)
target_link_libraries(test_liblxi liblxi::liblxi)

enable_testing()
add_test(NAME test_liblxi COMMAND test_liblxi)
