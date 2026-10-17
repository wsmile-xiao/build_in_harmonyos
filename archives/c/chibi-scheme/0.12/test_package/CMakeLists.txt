cmake_minimum_required(VERSION 3.15)
project(test_chibi-scheme C)

# Find the package via Conan-generated CMakeDeps
find_package(chibi-scheme REQUIRED)

add_executable(test_chibi-scheme test.c)
target_link_libraries(test_chibi-scheme chibi-scheme::chibi-scheme)

enable_testing()
add_test(NAME test_chibi-scheme COMMAND test_chibi-scheme)
