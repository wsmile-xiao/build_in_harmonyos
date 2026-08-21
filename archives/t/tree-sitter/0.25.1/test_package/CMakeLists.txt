cmake_minimum_required(VERSION 3.15)
project(test_tree-sitter C)

# Find the package via Conan-generated CMakeDeps
find_package(tree-sitter REQUIRED)

add_executable(test_tree-sitter test.c)
target_link_libraries(test_tree-sitter tree-sitter::tree-sitter)

enable_testing()
add_test(NAME test_tree-sitter COMMAND test_tree-sitter)
