cmake_minimum_required(VERSION 3.15)
project(test_slepc C)

# SLEPc public headers include PETSc headers, so consume both Conan targets.
find_package(slepc REQUIRED)
find_package(petsc REQUIRED)

add_executable(test_slepc test.c)
target_link_libraries(test_slepc slepc::slepc petsc::petsc)

enable_testing()
add_test(NAME test_slepc COMMAND test_slepc)
