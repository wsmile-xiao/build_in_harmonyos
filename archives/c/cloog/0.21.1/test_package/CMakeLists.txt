cmake_minimum_required(VERSION 3.15)
project(test_cloog C)

# Find the package via Conan-generated CMakeDeps
find_package(cloog REQUIRED)

add_executable(test_cloog test.c)
target_link_libraries(test_cloog cloog::cloog)

enable_testing()
add_test(NAME test_cloog COMMAND test_cloog)
