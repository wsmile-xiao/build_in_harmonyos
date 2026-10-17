cmake_minimum_required(VERSION 3.15)
project(test_avl C)

# Find the package via Conan-generated CMakeDeps
find_package(avl REQUIRED)

add_executable(test_avl test.c)
target_link_libraries(test_avl avl::avl)

enable_testing()
add_test(NAME test_avl COMMAND test_avl)
