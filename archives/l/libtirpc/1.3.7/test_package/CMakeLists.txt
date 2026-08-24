cmake_minimum_required(VERSION 3.15)
project(test_libtirpc C)

# Find the package via Conan-generated CMakeDeps
find_package(libtirpc REQUIRED)

add_executable(test_libtirpc test.c)
target_link_libraries(test_libtirpc libtirpc::libtirpc)

enable_testing()
add_test(NAME test_libtirpc COMMAND test_libtirpc)
