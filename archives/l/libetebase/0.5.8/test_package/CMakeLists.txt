cmake_minimum_required(VERSION 3.15)
project(test_libetebase C)

# Find the package via Conan-generated CMakeDeps
find_package(libetebase REQUIRED)

add_executable(test_libetebase test.c)
target_link_libraries(test_libetebase libetebase::etebase)

enable_testing()
add_test(NAME test_libetebase COMMAND test_libetebase)
