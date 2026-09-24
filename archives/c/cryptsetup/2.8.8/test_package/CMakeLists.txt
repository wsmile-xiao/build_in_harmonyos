cmake_minimum_required(VERSION 3.15)
project(test_cryptsetup C)

# Find the package via Conan-generated CMakeDeps
find_package(cryptsetup REQUIRED)

add_executable(test_cryptsetup test_cryptsetup.c)
target_link_libraries(test_cryptsetup cryptsetup::cryptsetup)

enable_testing()
add_test(NAME test_cryptsetup COMMAND test_cryptsetup)
