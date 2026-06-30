cmake_minimum_required(VERSION 3.15)
project(test_chadwick C)

# Find the package via Conan-generated CMakeDeps
find_package(chadwick REQUIRED)

add_executable(test_chadwick test.c)
target_link_libraries(test_chadwick chadwick::chadwick)

enable_testing()
add_test(NAME test_chadwick COMMAND test_chadwick)
