cmake_minimum_required(VERSION 3.15)
project(test_huffman C)

# Find the package via Conan-generated CMakeDeps
find_package(huffman REQUIRED)

add_executable(test_huffman test.c)
target_link_libraries(test_huffman huffman::huffman)

enable_testing()
add_test(NAME test_huffman COMMAND test_huffman)
