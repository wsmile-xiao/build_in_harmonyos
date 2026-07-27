cmake_minimum_required(VERSION 3.15)
project(test_turbo C)

# Find the package via Conan-generated CMakeDeps
find_package(turbo REQUIRED)

add_executable(test_turbo test.c)
target_link_libraries(test_turbo turbo::turbo)

enable_testing()
add_test(NAME test_turbo COMMAND test_turbo)
