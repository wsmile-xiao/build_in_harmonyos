cmake_minimum_required(VERSION 3.15)
project(test_madonctl C)

# Find the package via Conan-generated CMakeDeps
find_package(madonctl REQUIRED)

add_executable(test_madonctl test.c)
target_link_libraries(test_madonctl madonctl::madonctl)

enable_testing()
add_test(NAME test_madonctl COMMAND test_madonctl)
