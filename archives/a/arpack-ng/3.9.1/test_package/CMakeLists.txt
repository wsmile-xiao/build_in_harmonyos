cmake_minimum_required(VERSION 3.15)
project(test_arpack C)

# Find the package via Conan-generated CMakeDeps
find_package(arpack-ng REQUIRED)

add_executable(test_arpack test.c)
target_link_libraries(test_arpack arpack-ng::arpack-ng)

enable_testing()
add_test(NAME test_arpack COMMAND test_arpack)
