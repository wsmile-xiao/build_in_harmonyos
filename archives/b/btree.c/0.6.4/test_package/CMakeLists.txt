cmake_minimum_required(VERSION 3.15)
project(test_btree.c C)

# Find the package via Conan-generated CMakeDeps
find_package(btree.c REQUIRED)

add_executable(test_btree.c test.c)
target_link_libraries(test_btree.c btree.c::btree.c)

enable_testing()
add_test(NAME test_btree.c COMMAND test_btree.c)
