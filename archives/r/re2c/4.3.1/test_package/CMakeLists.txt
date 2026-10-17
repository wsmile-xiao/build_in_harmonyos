cmake_minimum_required(VERSION 3.15)
project(test_re2c C)

# The generated.c file is produced by re2c in build() step
# re2c processes test_input.c (containing re2c directives) and outputs generated.c
add_executable(test_re2c ${CMAKE_BINARY_DIR}/generated.c)

enable_testing()
add_test(NAME test_re2c COMMAND test_re2c)
