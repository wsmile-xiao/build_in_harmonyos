cmake_minimum_required(VERSION 3.15)
project(test_librg C)

# Find the package via Conan-generated CMakeDeps
find_package(librg REQUIRED)

add_executable(test_librg test.c)
target_link_libraries(test_librg librg::librg)

enable_testing()
add_test(NAME test_librg COMMAND test_librg)
