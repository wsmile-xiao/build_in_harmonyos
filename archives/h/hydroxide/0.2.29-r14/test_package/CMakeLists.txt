cmake_minimum_required(VERSION 3.15)
project(test_hydroxide C)

# Find the package via Conan-generated CMakeDeps
find_package(hydroxide REQUIRED)

add_executable(test_hydroxide test.c)
target_link_libraries(test_hydroxide hydroxide::hydroxide)

enable_testing()
add_test(NAME test_hydroxide COMMAND test_hydroxide)
