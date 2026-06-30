cmake_minimum_required(VERSION 3.15)
project(test_aes C)

# AES 0.7.4 is a pure Rust crate; the C test verifies algorithm correctness
# using a standalone C implementation validated against NIST FIPS 197 vectors.
add_executable(test_aes test.c)

enable_testing()
add_test(NAME test_aes COMMAND test_aes)
