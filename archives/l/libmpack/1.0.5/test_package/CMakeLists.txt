cmake_minimum_required(VERSION 3.15)
project(test_libmpack C)

# Find the package via Conan-generated CMakeDeps
find_package(libmpack REQUIRED)

add_executable(test_libmpack test.c)
target_link_libraries(test_libmpack libmpack::libmpack)

enable_testing()
add_test(NAME test_libmpack COMMAND test_libmpack)
