cmake_minimum_required(VERSION 3.15)
project(test_c89stringutils C)

# Find the package via Conan-generated CMakeDeps
find_package(c89stringutils REQUIRED)

add_executable(test_c89stringutils test.c)
target_link_libraries(test_c89stringutils c89stringutils::c89stringutils)

enable_testing()
add_test(NAME test_c89stringutils COMMAND test_c89stringutils)
