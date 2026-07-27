cmake_minimum_required(VERSION 3.15)
project(test_jsonnet C)

# Find the package via Conan-generated CMakeDeps
find_package(jsonnet REQUIRED)

add_executable(test_jsonnet test.c)
target_link_libraries(test_jsonnet jsonnet::jsonnet)

enable_testing()
add_test(NAME test_jsonnet COMMAND test_jsonnet)
