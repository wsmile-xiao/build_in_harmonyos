cmake_minimum_required(VERSION 3.15)
project(test_brainfuck C)

# Find the package via Conan-generated CMakeDeps
find_package(brainfuck REQUIRED)

add_executable(test_brainfuck test.c)
target_link_libraries(test_brainfuck brainfuck::brainfuck)

enable_testing()
add_test(NAME test_brainfuck COMMAND test_brainfuck)
