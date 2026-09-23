cmake_minimum_required(VERSION 3.15)
project(test_csiphash C)

# Find the package via Conan-generated CMakeDeps
find_package(c-siphash REQUIRED)

add_executable(test_csiphash test.c)
target_link_libraries(test_csiphash c-siphash::c-siphash)

enable_testing()
add_test(NAME test_csiphash COMMAND test_csiphash)
