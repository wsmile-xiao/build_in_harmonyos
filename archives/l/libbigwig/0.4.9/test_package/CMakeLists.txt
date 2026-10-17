cmake_minimum_required(VERSION 3.15)
project(test_libbigwig C)

# Find the package via Conan-generated CMakeDeps
find_package(libbigwig REQUIRED)

add_executable(test_libbigwig test.c)
target_link_libraries(test_libbigwig libbigwig::libbigwig)

enable_testing()
add_test(NAME test_libbigwig COMMAND test_libbigwig)
