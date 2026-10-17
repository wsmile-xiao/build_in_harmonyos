cmake_minimum_required(VERSION 3.15)
project(test_tbox C)

# Find the package via Conan-generated CMakeDeps
find_package(tbox REQUIRED)

add_executable(test_tbox test.c)
target_link_libraries(test_tbox tbox::tbox)

enable_testing()
add_test(NAME test_tbox COMMAND test_tbox)
