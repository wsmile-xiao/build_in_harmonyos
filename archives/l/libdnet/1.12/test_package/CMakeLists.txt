cmake_minimum_required(VERSION 3.15)
project(test_libdnet C)

# Find the package via Conan-generated CMakeDeps
find_package(libdnet REQUIRED)

add_executable(test_libdnet test.c)
target_link_libraries(test_libdnet libdnet::libdnet)

enable_testing()
add_test(NAME test_libdnet COMMAND test_libdnet)
