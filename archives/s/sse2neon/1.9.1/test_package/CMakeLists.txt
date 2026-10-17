cmake_minimum_required(VERSION 3.15)
project(test_sse2neon C)

# Find the package via Conan-generated CMakeDeps
find_package(sse2neon REQUIRED)

add_executable(test_sse2neon test.c)
target_link_libraries(test_sse2neon sse2neon::sse2neon)

enable_testing()
add_test(NAME test_sse2neon COMMAND test_sse2neon)
