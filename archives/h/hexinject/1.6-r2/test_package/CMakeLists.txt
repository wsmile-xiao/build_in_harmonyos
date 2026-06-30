cmake_minimum_required(VERSION 3.15)
project(test_hexinject C)

# Find the package via Conan-generated CMakeDeps
find_package(hexinject REQUIRED)

add_executable(test_hexinject test.c)
target_link_libraries(test_hexinject hexinject::hexinject)

enable_testing()
add_test(NAME test_hexinject COMMAND test_hexinject)
