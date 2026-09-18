cmake_minimum_required(VERSION 3.15)
project(test_irrtoolset C)

# Find the package via Conan-generated CMakeDeps
find_package(irrtoolset REQUIRED)

add_executable(test_irrtoolset test.c)
target_link_libraries(test_irrtoolset irrtoolset::irrtoolset)

enable_testing()
add_test(NAME test_irrtoolset COMMAND test_irrtoolset)
