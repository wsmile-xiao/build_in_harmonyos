cmake_minimum_required(VERSION 3.15)
project(test_qsort C)

# Find the package via Conan-generated CMakeDeps
find_package(qsort REQUIRED)

add_executable(test_qsort test.c)
target_link_libraries(test_qsort qsort::qsort)

enable_testing()
add_test(NAME test_qsort COMMAND test_qsort)
