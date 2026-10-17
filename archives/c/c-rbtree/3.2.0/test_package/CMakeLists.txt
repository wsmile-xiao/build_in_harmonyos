cmake_minimum_required(VERSION 3.15)
project(test_crbtree C)

# Find the package via Conan-generated CMakeDeps
find_package(c-rbtree REQUIRED)

add_executable(test_crbtree test.c)
target_link_libraries(test_crbtree c-rbtree::c-rbtree)

enable_testing()
add_test(NAME test_crbtree COMMAND test_crbtree)
