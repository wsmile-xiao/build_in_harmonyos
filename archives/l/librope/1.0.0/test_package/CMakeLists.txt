cmake_minimum_required(VERSION 3.15)
project(test_librope C)

# Find the package via Conan-generated CMakeDeps
find_package(librope REQUIRED)

add_executable(test_librope test.c)
target_link_libraries(test_librope librope::librope)

enable_testing()
add_test(NAME test_librope COMMAND test_librope)
