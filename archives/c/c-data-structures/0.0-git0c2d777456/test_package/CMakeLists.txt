cmake_minimum_required(VERSION 3.15)
project(test_c-data-structures C)

# Find the package via Conan-generated CMakeDeps (package name uses hyphens)
find_package(c-data-structures REQUIRED)

add_executable(test_c-data-structures test.c)
target_link_libraries(test_c-data-structures c-data-structures::c-data-structures)

enable_testing()
add_test(NAME test_c-data-structures COMMAND test_c-data-structures)