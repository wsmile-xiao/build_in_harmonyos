cmake_minimum_required(VERSION 3.15)
project(test_utf8proc C)

# Find the package via Conan-generated CMakeDeps
find_package(utf8proc REQUIRED)

add_executable(test_utf8proc test.c)
target_link_libraries(test_utf8proc utf8proc::utf8proc)

enable_testing()
add_test(NAME test_utf8proc COMMAND test_utf8proc)
