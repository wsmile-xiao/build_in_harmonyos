cmake_minimum_required(VERSION 3.15)
project(test_cutf8 C)

# Find the package via Conan-generated CMakeDeps
find_package(c-utf8 REQUIRED)

add_executable(test_cutf8 test.c)
target_link_libraries(test_cutf8 c-utf8::c-utf8)

enable_testing()
add_test(NAME test_cutf8 COMMAND test_cutf8)
