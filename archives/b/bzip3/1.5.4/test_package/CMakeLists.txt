cmake_minimum_required(VERSION 3.15)
project(test_bzip3 C)

# Find the package via Conan-generated CMakeDeps
find_package(bzip3 REQUIRED)

add_executable(test_bzip3 test.c)
target_link_libraries(test_bzip3 bzip3::bz3)

enable_testing()
add_test(NAME test_bzip3 COMMAND test_bzip3)