cmake_minimum_required(VERSION 3.15)
project(test_isal_crypto C)

# Find the package via Conan-generated CMakeDeps
find_package(ISALCrypto REQUIRED)

add_executable(test_isal_crypto test.c)
target_link_libraries(test_isal_crypto ISALCrypto::isal_crypto)

enable_testing()
add_test(NAME test_isal_crypto COMMAND test_isal_crypto)
