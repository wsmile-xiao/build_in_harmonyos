cmake_minimum_required(VERSION 3.15)
project(test_libbcrypt C)

# Find the package via Conan-generated CMakeDeps
find_package(libbcrypt REQUIRED)

add_executable(test_libbcrypt test.c)
target_link_libraries(test_libbcrypt libbcrypt::libbcrypt)

enable_testing()
add_test(NAME test_libbcrypt COMMAND test_libbcrypt)
