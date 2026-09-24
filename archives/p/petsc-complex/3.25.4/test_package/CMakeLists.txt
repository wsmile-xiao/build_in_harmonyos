cmake_minimum_required(VERSION 3.15)
project(test_petsc_complex C)

# Find the package through the Conan-generated CMakeDeps files.
find_package(petsc-complex REQUIRED)

add_executable(test_petsc_complex test.c)
target_link_libraries(test_petsc_complex petsc-complex::petsc-complex)

enable_testing()
add_test(NAME test_petsc_complex COMMAND test_petsc_complex)
