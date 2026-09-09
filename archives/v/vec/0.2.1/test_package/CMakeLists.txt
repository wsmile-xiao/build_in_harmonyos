cmake_minimum_required(VERSION 3.15)
project(test_vec C)

# Find the package via Conan-generated CMakeDeps
find_package(vec REQUIRED)

add_executable(test_vec test.c)
target_link_libraries(test_vec vec::vec)

enable_testing()
add_test(NAME test_vec COMMAND test_vec)
