cmake_minimum_required(VERSION 3.15)
project(test_flashrom C)

# Find the package via Conan-generated CMakeDeps
find_package(flashrom REQUIRED)

add_executable(test_flashrom test.c)
target_link_libraries(test_flashrom flashrom::flashrom)

enable_testing()
add_test(NAME test_flashrom COMMAND test_flashrom)
