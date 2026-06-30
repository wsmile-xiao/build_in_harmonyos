cmake_minimum_required(VERSION 3.15)
project(test_dsnet C)

# Find the package via Conan-generated CMakeDeps
find_package(dsnet REQUIRED)

add_executable(test_dsnet test.c)
target_link_libraries(test_dsnet dsnet::dsnet)

enable_testing()
add_test(NAME test_dsnet COMMAND test_dsnet)
