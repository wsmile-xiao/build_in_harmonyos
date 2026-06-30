cmake_minimum_required(VERSION 3.15)
project(test_fmilibrary C)

# Find the package via Conan-generated CMakeDeps
find_package(fmilibrary REQUIRED)

add_executable(test_fmilibrary test.c)
target_link_libraries(test_fmilibrary fmilibrary::fmilibrary)

enable_testing()
add_test(NAME test_fmilibrary COMMAND test_fmilibrary)
