cmake_minimum_required(VERSION 3.15)
project(test_superlu C)

# Find the package via Conan-generated CMakeDeps
find_package(superlu REQUIRED)

add_executable(test_superlu test.c)
target_link_libraries(test_superlu superlu::superlu)

enable_testing()
add_test(NAME test_superlu COMMAND test_superlu)
