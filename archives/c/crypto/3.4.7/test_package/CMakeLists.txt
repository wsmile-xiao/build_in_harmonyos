cmake_minimum_required(VERSION 3.15)
project(test_crypto C)

# Find the package via Conan-generated CMakeDeps
find_package(crypto REQUIRED)

add_executable(test_crypto test.c)
target_link_libraries(test_crypto crypto::crypto)

enable_testing()
add_test(NAME test_crypto COMMAND test_crypto)
