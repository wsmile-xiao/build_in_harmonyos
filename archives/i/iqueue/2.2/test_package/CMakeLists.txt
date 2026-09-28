cmake_minimum_required(VERSION 3.15)
project(test_iqueue C)

# Find the package via Conan-generated CMakeDeps
find_package(iqueue REQUIRED)

add_executable(test_iqueue test.c)
target_link_libraries(test_iqueue iqueue::iqueue)

enable_testing()
add_test(NAME test_iqueue COMMAND test_iqueue)
