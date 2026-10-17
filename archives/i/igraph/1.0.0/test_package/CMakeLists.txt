cmake_minimum_required(VERSION 3.15)
project(test_igraph C)

# Find the package via Conan-generated CMakeDeps
find_package(igraph REQUIRED)

add_executable(test_igraph test.c)
target_link_libraries(test_igraph igraph::igraph)

enable_testing()
add_test(NAME test_igraph COMMAND test_igraph)
