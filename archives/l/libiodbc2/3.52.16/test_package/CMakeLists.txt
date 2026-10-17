cmake_minimum_required(VERSION 3.15)
project(test_libiodbc2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libiodbc2 REQUIRED)

add_executable(test_libiodbc2 test.c)
target_link_libraries(test_libiodbc2 libiodbc2::libiodbc2)

enable_testing()
add_test(NAME test_libiodbc2 COMMAND test_libiodbc2)
