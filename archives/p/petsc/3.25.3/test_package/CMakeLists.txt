cmake_minimum_required(VERSION 3.15)
project(test_petsc C)

# Find the package via Conan-generated CMakeDeps
find_package(petsc REQUIRED)

add_executable(test_petsc test.c)
target_link_libraries(test_petsc petsc::petsc)

enable_testing()
add_test(NAME test_petsc COMMAND test_petsc)
