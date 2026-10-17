cmake_minimum_required(VERSION 3.15)
project(test_bptree C)

# Find the package via Conan-generated CMakeDeps
find_package(bptree REQUIRED)

add_executable(test_bptree test.c)
target_link_libraries(test_bptree bptree::bptree)

enable_testing()
add_test(NAME test_bptree COMMAND test_bptree)
