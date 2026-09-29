cmake_minimum_required(VERSION 3.15)
project(test_libpqueue C)

# Find the package via Conan-generated CMakeDeps
find_package(libpqueue REQUIRED)

add_executable(test_libpqueue test.c)
target_link_libraries(test_libpqueue libpqueue::libpqueue)

enable_testing()
add_test(NAME test_libpqueue COMMAND test_libpqueue)
