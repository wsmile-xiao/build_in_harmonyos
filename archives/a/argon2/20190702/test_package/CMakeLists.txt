cmake_minimum_required(VERSION 3.15)
project(test_argon2 C)

# Find the package via Conan-generated CMakeDeps
find_package(argon2 REQUIRED)

add_executable(test_argon2 test.c)
target_link_libraries(test_argon2 argon2::argon2)

enable_testing()
add_test(NAME test_argon2 COMMAND test_argon2)
