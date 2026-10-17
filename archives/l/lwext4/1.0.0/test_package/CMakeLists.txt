cmake_minimum_required(VERSION 3.15)
project(test_lwext4 C)

# Find the package via Conan-generated CMakeDeps
find_package(lwext4 REQUIRED)

add_executable(test_lwext4 test.c)
target_link_libraries(test_lwext4 lwext4::lwext4)

enable_testing()
add_test(NAME test_lwext4 COMMAND test_lwext4)
