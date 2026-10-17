cmake_minimum_required(VERSION 3.15)
project(test_ell C)

# Find the package via Conan-generated CMakeDeps
find_package(ell REQUIRED)

add_executable(test_ell test.c)
target_link_libraries(test_ell ell::ell)

enable_testing()
add_test(NAME test_ell COMMAND test_ell)
