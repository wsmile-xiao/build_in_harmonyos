cmake_minimum_required(VERSION 3.15)
project(test_schism C)

# Find the package via Conan-generated CMakeDeps
find_package(schism REQUIRED)

add_executable(test_schism test.c)
target_link_libraries(test_schism schism::schism)

enable_testing()
add_test(NAME test_schism COMMAND test_schism)
