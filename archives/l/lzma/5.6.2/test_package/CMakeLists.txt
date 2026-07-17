cmake_minimum_required(VERSION 3.15)
project(test_lzma C)

# Find the package via Conan-generated CMakeDeps
find_package(lzma REQUIRED)

add_executable(test_lzma test.c)
target_link_libraries(test_lzma lzma::lzma)

enable_testing()
add_test(NAME test_lzma COMMAND test_lzma)
