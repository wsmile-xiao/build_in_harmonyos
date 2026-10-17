cmake_minimum_required(VERSION 3.15)
project(test_gperftools C)

# Find the package via Conan-generated CMakeDeps
find_package(gperftools REQUIRED)

add_executable(test_gperftools test.c)
target_link_libraries(test_gperftools gperftools::tcmalloc_minimal)

enable_testing()
add_test(NAME test_gperftools COMMAND test_gperftools)
