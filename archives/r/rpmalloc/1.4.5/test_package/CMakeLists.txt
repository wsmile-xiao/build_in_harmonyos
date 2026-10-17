cmake_minimum_required(VERSION 3.15)
project(test_rpmalloc C)

# Find the package via Conan-generated CMakeDeps
find_package(rpmalloc REQUIRED)

add_executable(test_rpmalloc test.c)
target_link_libraries(test_rpmalloc rpmalloc::rpmalloc)

enable_testing()
add_test(NAME test_rpmalloc COMMAND test_rpmalloc)
