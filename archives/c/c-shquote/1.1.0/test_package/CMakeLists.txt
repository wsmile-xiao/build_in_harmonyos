cmake_minimum_required(VERSION 3.15)
project(test_cshquote C)

# Find the package via Conan-generated CMakeDeps
find_package(c-shquote REQUIRED)

add_executable(test_cshquote test.c)
target_link_libraries(test_cshquote c-shquote::c-shquote)

enable_testing()
add_test(NAME test_cshquote COMMAND test_cshquote)
