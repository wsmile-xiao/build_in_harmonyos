cmake_minimum_required(VERSION 3.15)
project(test_libutf8proc C)

# Find the package via Conan-generated CMakeDeps
find_package(libutf8proc REQUIRED)

add_executable(test_libutf8proc test.c)
target_link_libraries(test_libutf8proc libutf8proc::libutf8proc)

enable_testing()
add_test(NAME test_libutf8proc COMMAND test_libutf8proc)
