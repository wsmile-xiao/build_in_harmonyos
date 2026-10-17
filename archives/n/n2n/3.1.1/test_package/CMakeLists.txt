cmake_minimum_required(VERSION 3.15)
project(test_n2n C)

# Find the package via Conan-generated CMakeDeps
find_package(n2n REQUIRED)

add_executable(test_n2n test.c)
target_link_libraries(test_n2n n2n::n2n)

enable_testing()
add_test(NAME test_n2n COMMAND test_n2n)
