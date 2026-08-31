cmake_minimum_required(VERSION 3.15)
project(test_bambootracker C)

# Find the package via Conan-generated CMakeDeps
find_package(bambootracker REQUIRED)

add_executable(test_bambootracker test.c)
target_link_libraries(test_bambootracker bambootracker::bambootracker)

enable_testing()
add_test(NAME test_bambootracker COMMAND test_bambootracker)
