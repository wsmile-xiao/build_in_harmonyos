cmake_minimum_required(VERSION 3.15)
project(ntbtls_consumer C)

# Find the package via Conan-generated CMakeDeps
find_package(ntbtls REQUIRED)

add_executable(ntbtls_consumer test.c)
target_link_libraries(ntbtls_consumer ntbtls::ntbtls)

enable_testing()
add_test(NAME ntbtls_consumer COMMAND ntbtls_consumer)
