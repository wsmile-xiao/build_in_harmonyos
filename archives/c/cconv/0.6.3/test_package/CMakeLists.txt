cmake_minimum_required(VERSION 3.15)
project(test_cconv C)

# Find the package via Conan-generated CMakeDeps
find_package(cconv REQUIRED)

add_executable(test_cconv test.c)
target_link_libraries(test_cconv cconv::cconv)

enable_testing()
add_test(NAME test_cconv COMMAND test_cconv)
