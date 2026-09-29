cmake_minimum_required(VERSION 3.15)
project(test_math-sll C)

# Find the package via Conan-generated CMakeDeps
find_package(math-sll REQUIRED)

add_executable(test_math-sll test.c)
target_link_libraries(test_math-sll math-sll::math-sll)

enable_testing()
add_test(NAME test_math-sll COMMAND test_math-sll)
