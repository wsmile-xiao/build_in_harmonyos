cmake_minimum_required(VERSION 3.15)
project(test_levenshtein.c C)

# Find the package via Conan-generated CMakeDeps
find_package(levenshtein.c REQUIRED)

add_executable(test_levenshtein.c test.c)
target_link_libraries(test_levenshtein.c levenshtein.c::levenshtein.c)

enable_testing()
add_test(NAME test_levenshtein.c COMMAND test_levenshtein.c)
