cmake_minimum_required(VERSION 3.15)
project(test_z3 C)

# Find the package via Conan-generated CMakeDeps
find_package(Z3 REQUIRED)

add_executable(test_z3 test.c)
target_link_libraries(test_z3 z3::libz3)

enable_testing()
add_test(NAME test_z3 COMMAND test_z3)
