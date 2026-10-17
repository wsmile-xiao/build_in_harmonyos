cmake_minimum_required(VERSION 3.15)
project(test_lfortran_runtime C)

# Find the package via Conan-generated CMakeDeps
find_package(lfortran-runtime REQUIRED)

add_executable(test_lfortran_runtime test_lfortran_runtime.c)
target_link_libraries(test_lfortran_runtime lfortran-runtime::lfortran-runtime)

enable_testing()
add_test(NAME test_lfortran_runtime COMMAND test_lfortran_runtime)
