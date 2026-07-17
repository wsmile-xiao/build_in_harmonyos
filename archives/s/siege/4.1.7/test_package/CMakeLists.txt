cmake_minimum_required(VERSION 3.15)
project(test_siege C)

# Find the package via Conan-generated CMakeDeps
find_package(siege REQUIRED)

add_executable(test_siege test.c)
target_link_libraries(test_siege siege::siege)

enable_testing()
add_test(NAME test_siege COMMAND test_siege)
