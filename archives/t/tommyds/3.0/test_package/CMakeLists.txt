cmake_minimum_required(VERSION 3.15)
project(test_tommyds C)

# Find the package via Conan-generated CMakeDeps
find_package(tommyds REQUIRED)

add_executable(test_tommyds test.c)
target_link_libraries(test_tommyds tommyds::tommyds)

enable_testing()
add_test(NAME test_tommyds COMMAND test_tommyds)
