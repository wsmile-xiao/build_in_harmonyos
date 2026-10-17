cmake_minimum_required(VERSION 3.15)
project(test_libfort C)

# Find the package via Conan-generated CMakeDeps
find_package(libfort REQUIRED)

add_executable(test_libfort test.c)
target_link_libraries(test_libfort libfort::fort)

enable_testing()
add_test(NAME test_libfort COMMAND test_libfort)
