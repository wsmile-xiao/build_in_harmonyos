cmake_minimum_required(VERSION 3.15)
project(test_lzo2 C)

# Find the package via Conan-generated CMakeDeps
find_package(lzo2 REQUIRED)

add_executable(test_lzo2 test.c)
target_link_libraries(test_lzo2 lzo2::lzo2)

enable_testing()
add_test(NAME test_lzo2 COMMAND test_lzo2)
