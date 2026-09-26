cmake_minimum_required(VERSION 3.15)
project(test_lfqueue C)

# Find the package via Conan-generated CMakeDeps
find_package(lfqueue REQUIRED)

add_executable(test_lfqueue test.c)
target_link_libraries(test_lfqueue lfqueue::lfqueue)

enable_testing()
add_test(NAME test_lfqueue COMMAND test_lfqueue)
