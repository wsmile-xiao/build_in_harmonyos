cmake_minimum_required(VERSION 3.15)
project(test_wolfssl C)

# Find the package via Conan-generated CMakeDeps
find_package(wolfssl REQUIRED)

add_executable(test_wolfssl test.c)
target_link_libraries(test_wolfssl wolfssl::wolfssl)

enable_testing()
add_test(NAME test_wolfssl COMMAND test_wolfssl)