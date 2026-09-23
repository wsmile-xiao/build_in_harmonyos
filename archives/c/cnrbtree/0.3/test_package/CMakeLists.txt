cmake_minimum_required(VERSION 3.15)
project(test_cnrbtree C)

# Find the package via Conan-generated CMakeDeps
find_package(cnrbtree REQUIRED)

add_executable(test_cnrbtree test.c)
target_link_libraries(test_cnrbtree cnrbtree::cnrbtree)

enable_testing()
add_test(NAME test_cnrbtree COMMAND test_cnrbtree)
