cmake_minimum_required(VERSION 3.15)
project(test_libb2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libb2 REQUIRED)

add_executable(test_libb2 test.c)
target_link_libraries(test_libb2 libb2::libb2)

enable_testing()
add_test(NAME test_libb2 COMMAND test_libb2)
