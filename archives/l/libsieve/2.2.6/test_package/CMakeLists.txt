cmake_minimum_required(VERSION 3.15)
project(test_libsieve C)

# Find the package via Conan-generated CMakeDeps
find_package(libsieve REQUIRED)

add_executable(test_sieve test_sieve.c)
target_link_libraries(test_sieve libsieve::libsieve)

add_executable(test_sieve_invalid test_sieve_invalid.c)
target_link_libraries(test_sieve_invalid libsieve::libsieve)

enable_testing()
add_test(NAME test_sieve COMMAND test_sieve)
add_test(NAME test_sieve_invalid COMMAND test_sieve_invalid)
