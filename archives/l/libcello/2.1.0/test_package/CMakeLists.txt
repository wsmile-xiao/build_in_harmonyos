cmake_minimum_required(VERSION 3.15)
project(test_cello C)

# Find the package via Conan-generated CMakeDeps
find_package(libcello REQUIRED)

add_executable(test_cello test.c)
target_link_libraries(test_cello libcello::libcello)

enable_testing()
add_test(NAME test_cello COMMAND test_cello)
